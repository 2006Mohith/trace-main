from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Case, Suspect, CDRRecord, IPDRRecord, Event
from schemas import (
    SuspectOut, SuspectProfileOut, CDRSummary, IPDRSummary,
    OTTUsageRow, MovementPoint, CallHeatmapRow, EventOut,
    NetworkGraphOut, GraphNode, GraphEdge,
)
from collections import Counter
from itertools import groupby

router = APIRouter(tags=["suspects"])


def _s(v) -> str:
    """Safely coerce any value (bytes, numpy str, etc.) to native Python str."""
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return str(v) if v is not None else ""


def _suspect_out(s: Suspect, db: Session) -> SuspectOut:
    events = _events_for_suspect(s.case_id, s.label, db)
    event_count = len(events)
    anomaly_event = next((ev for ev in events if ev.event_type == "ANOMALY"), None)
    anomaly_score = anomaly_event.detail.get("anomaly_score") if anomaly_event else None
    return SuspectOut(
        id=_s(s.id),
        case_id=_s(s.case_id),
        label=_s(s.label),
        primary_msisdn=_s(s.primary_msisdn),
        anomaly_score=anomaly_score,
        event_count=event_count,
    )


def _events_for_suspect(case_id: str, suspect_label: str, db: Session) -> List[Event]:
    """Return events for a case where suspect_label is in involved_suspects (Python filter)."""
    all_events = db.query(Event).filter(Event.case_id == case_id).all()
    return [ev for ev in all_events if suspect_label in (ev.involved_suspects or [])]


@router.get("/cases/{case_id}/suspects", response_model=List[SuspectOut])
def list_suspects(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    return [_suspect_out(s, db) for s in suspects]


@router.get("/cases/{case_id}/network", response_model=NetworkGraphOut)
def get_network(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    suspect_map = {s.primary_msisdn: s for s in suspects}

    # Find common contact numbers from events
    common_events = db.query(Event).filter(
        Event.case_id == case_id,
        Event.event_type == "COMMON_CONTACT",
    ).all()
    common_numbers = set()
    for ev in common_events:
        cn = ev.detail.get("common_number")
        if cn:
            common_numbers.add(cn)

    nodes: List[GraphNode] = []
    for s in suspects:
        nodes.append(GraphNode(id=_s(s.id), label=_s(s.label), node_type="suspect", suspect_id=_s(s.id)))
    for num in common_numbers:
        nodes.append(GraphNode(id=f"contact_{num}", label=num[-4:], node_type="contact"))

    # Build edges from CDR — between suspects and to common contacts
    edges_map: dict = {}
    for s in suspects:
        cdrs = db.query(CDRRecord).filter(CDRRecord.suspect_id == s.id).all()
        for rec in cdrs:
            target_suspect = suspect_map.get(rec.msisdn_b)
            if target_suspect and target_suspect.id != s.id:
                key = tuple(sorted([s.id, target_suspect.id]))
                if key not in edges_map:
                    edges_map[key] = {"call_count": 0, "total_duration_sec": 0}
                edges_map[key]["call_count"] += 1
                edges_map[key]["total_duration_sec"] += rec.duration_sec or 0
            if rec.msisdn_b in common_numbers:
                key = (s.id, f"contact_{rec.msisdn_b}")
                if key not in edges_map:
                    edges_map[key] = {"call_count": 0, "total_duration_sec": 0}
                edges_map[key]["call_count"] += 1
                edges_map[key]["total_duration_sec"] += rec.duration_sec or 0

    edges = [
        GraphEdge(source=k[0], target=k[1], call_count=v["call_count"], total_duration_sec=v["total_duration_sec"])
        for k, v in edges_map.items()
    ]

    return NetworkGraphOut(nodes=nodes, edges=edges)


@router.get("/suspects/{suspect_id}/profile", response_model=SuspectProfileOut)
def get_suspect_profile(suspect_id: str, db: Session = Depends(get_db)):
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")

    cdrs = db.query(CDRRecord).filter(CDRRecord.suspect_id == suspect_id).all()
    ipdrs = db.query(IPDRRecord).filter(IPDRRecord.suspect_id == suspect_id).all()

    # ── CDR Summary ──────────────────────────────────────────────────────────
    cdr_summary = None
    if cdrs:
        calls = [r for r in cdrs if r.call_type == "CALL"]
        sms = [r for r in cdrs if r.call_type == "SMS"]
        contacts = set(r.msisdn_b for r in cdrs)
        durations = [r.duration_sec for r in calls if r.duration_sec]
        avg_dur = sum(durations) / len(durations) if durations else 0

        night_calls = [r for r in calls if r.timestamp.hour >= 23 or r.timestamp.hour < 5]
        night_ratio = len(night_calls) / len(calls) if calls else 0

        bins: Counter = Counter()
        for r in cdrs:
            bucket = (r.timestamp.date(), r.timestamp.hour // 6)
            bins[bucket] += 1
        max_bin = max(bins.values()) if bins else 0
        avg_bin = sum(bins.values()) / len(bins) if bins else 0
        burst = max_bin / avg_bin if avg_bin > 0 else 0

        # Anomaly score from events (Python-filtered)
        anomaly_events = _events_for_suspect(suspect.case_id, suspect.label, db)
        anomaly_event = next(
            (ev for ev in anomaly_events if ev.event_type == "ANOMALY"), None
        )
        anomaly_score = anomaly_event.detail.get("anomaly_score") if anomaly_event else None

        cdr_summary = CDRSummary(
            total_calls=len(calls),
            total_sms=len(sms),
            unique_contacts=len(contacts),
            avg_duration_sec=round(avg_dur, 1),
            night_call_ratio=round(night_ratio, 3),
            burst_score=round(burst, 2),
            anomaly_score=anomaly_score,
        )

    # ── IPDR Summary ─────────────────────────────────────────────────────────
    ipdr_summary = None
    if ipdrs:
        sorted_ipdrs = sorted(ipdrs, key=lambda x: x.app_label or "Unknown")
        ott_rows = []
        for app, group in groupby(sorted_ipdrs, key=lambda x: x.app_label or "Unknown"):
            recs = list(group)
            timestamps = [r.timestamp for r in recs]
            ott_rows.append(OTTUsageRow(
                app=app,
                session_count=len(recs),
                total_data_kb=round(sum(r.data_volume_kb or 0 for r in recs), 2),
                first_seen=min(timestamps) if timestamps else None,
                last_seen=max(timestamps) if timestamps else None,
            ))
        ipdr_summary = IPDRSummary(
            total_sessions=len(ipdrs),
            total_data_kb=round(sum(r.data_volume_kb or 0 for r in ipdrs), 2),
            ott_breakdown=ott_rows,
        )

    # ── Events for this suspect (Python-level filter) ────────────────────────
    events_raw = sorted(
        _events_for_suspect(suspect.case_id, suspect.label, db),
        key=lambda ev: ev.occurred_at or datetime.min,
        reverse=True,
    )
    events = [
        EventOut(
            id=ev.id, case_id=ev.case_id, event_type=ev.event_type,
            severity=ev.severity, involved_suspects=ev.involved_suspects or [],
            detail=ev.detail, occurred_at=ev.occurred_at,
        )
        for ev in events_raw
    ]

    # ── Call heatmap ─────────────────────────────────────────────────────────
    heatmap_map: dict = {}
    for rec in cdrs:
        key = (rec.timestamp.weekday(), rec.timestamp.hour)
        heatmap_map[key] = heatmap_map.get(key, 0) + 1
    heatmap = [
        CallHeatmapRow(day_of_week=k[0], hour_of_day=k[1], call_count=v)
        for k, v in heatmap_map.items()
    ]

    # ── Movement ─────────────────────────────────────────────────────────────
    co_location_towers: dict = {}
    for ev in events_raw:
        if ev.event_type == "CO_LOCATION":
            tid = ev.detail.get("tower_id")
            others = [s for s in (ev.involved_suspects or []) if s != suspect.label]
            if tid:
                co_location_towers[tid] = others

    movement = []
    tower_cdrs = sorted(
        [r for r in cdrs if r.tower_id and r.tower_lat is not None and r.tower_lon is not None],
        key=lambda r: r.timestamp,
    )
    seen = set()
    for rec in tower_cdrs:
        key = (rec.tower_id, rec.timestamp.date())
        if key in seen:
            continue
        seen.add(key)
        co_loc = rec.tower_id in co_location_towers
        movement.append(MovementPoint(
            tower_id=rec.tower_id,
            lat=rec.tower_lat,
            lon=rec.tower_lon,
            timestamp=rec.timestamp,
            co_location=co_loc,
            co_location_with=co_location_towers.get(rec.tower_id, []),
        ))

    return SuspectProfileOut(
        suspect=_suspect_out(suspect, db),
        cdr_summary=cdr_summary,
        ipdr_summary=ipdr_summary,
        events=events,
        call_heatmap_data=heatmap,
        movement_data=movement,
    )


@router.get("/suspects/{suspect_id}/movement", response_model=List[MovementPoint])
def get_movement(suspect_id: str, db: Session = Depends(get_db)):
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
    profile = get_suspect_profile(suspect_id, db)
    return profile.movement_data


@router.get("/suspects/{suspect_id}/call_heatmap", response_model=List[CallHeatmapRow])
def get_call_heatmap(suspect_id: str, db: Session = Depends(get_db)):
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
    profile = get_suspect_profile(suspect_id, db)
    return profile.call_heatmap_data


@router.delete("/suspects/{suspect_id}", status_code=204)
def delete_suspect(suspect_id: str, db: Session = Depends(get_db)):
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
    db.delete(suspect)
    db.commit()
    return None


@router.get("/cases/{case_id}/shared-contacts")
def get_shared_contacts(case_id: str, db: Session = Depends(get_db)):
    """Returns phone numbers that appear in CDRs of 2+ suspects in the same case."""
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()

    contact_map: dict = {}
    contact_counts: dict = {}

    for suspect in suspects:
        cdrs = db.query(CDRRecord).filter(CDRRecord.suspect_id == suspect.id).all()
        for cdr in cdrs:
            num = cdr.msisdn_b
            if not num:
                continue
            if num not in contact_map:
                contact_map[num] = set()
                contact_counts[num] = 0
            contact_map[num].add(suspect.label)
            contact_counts[num] += 1

    shared = [
        {
            "number": num,
            "suspects": sorted(list(labels)),
            "total_calls": contact_counts[num],
            "suspect_count": len(labels),
        }
        for num, labels in contact_map.items()
        if len(labels) >= 2
    ]
    shared.sort(key=lambda x: x["suspect_count"], reverse=True)
    return shared[:20]


@router.get("/global/handler-numbers")
def get_global_handlers(db: Session = Depends(get_db)):
    """Finds numbers that appear across multiple different cases (potential cross-case handlers)."""
    from sqlalchemy import func

    results = (
        db.query(CDRRecord.msisdn_b, Suspect.case_id, func.count(CDRRecord.id).label("cnt"))
        .join(Suspect, CDRRecord.suspect_id == Suspect.id)
        .group_by(CDRRecord.msisdn_b, Suspect.case_id)
        .all()
    )

    number_cases: dict = {}
    number_calls: dict = {}
    for msisdn_b, case_id, cnt in results:
        if not msisdn_b:
            continue
        if msisdn_b not in number_cases:
            number_cases[msisdn_b] = set()
            number_calls[msisdn_b] = 0
        number_cases[msisdn_b].add(case_id)
        number_calls[msisdn_b] += cnt

    cross_case = [
        {"number": num, "case_count": len(cases), "total_calls": number_calls[num]}
        for num, cases in number_cases.items()
        if len(cases) >= 2
    ]
    cross_case.sort(key=lambda x: x["case_count"], reverse=True)
    return cross_case
