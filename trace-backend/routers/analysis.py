from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Case, Suspect, Event
from schemas import AnalysisSummary

# ── Original engines ───────────────────────────────────────────────────────────
from engines.imei_swap import detect_imei_swaps, detect_multi_sim_imei
from engines.co_location import detect_co_location
from engines.common_contact import detect_common_contacts
from engines.anomaly import detect_anomalies
from engines.ott_fingerprint import fingerprint_ott

# ── New engines ────────────────────────────────────────────────────────────────
from engines.cross_case import detect_cross_case_handlers
from engines.tower_silence import detect_tower_silence
from engines.night_loop import detect_night_and_loop_calls
from routers.audit import log_audit

router = APIRouter(tags=["analysis"])


@router.post("/cases/{case_id}/analyze", response_model=AnalysisSummary)
def run_analysis(case_id: str, request: Request, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    if not suspects:
        raise HTTPException(status_code=422, detail="No suspects uploaded for this case")

    # Delete existing events for this case to avoid duplicates on re-analysis
    db.query(Event).filter(Event.case_id == case_id).delete()

    counts = {
        "imei_swaps": 0,
        "multi_sim_imei": 0,
        "co_locations": 0,
        "common_contacts": 0,
        "anomalies": 0,
        "ott_flags": 0,
        "cross_case_handlers": 0,
        "tower_silence": 0,
        "night_call_bursts": 0,
        "loop_calls": 0,
    }

    # Engine 1a: IMEI swap — per suspect
    for suspect in suspects:
        events = detect_imei_swaps(suspect.id, db)
        for ev in events:
            db.add(ev)
        counts["imei_swaps"] += len(events)

    # Engine 1b: Multi-SIM / Burner phone — case-wide
    multi_sim_events = detect_multi_sim_imei(case_id, db)
    for ev in multi_sim_events:
        db.add(ev)
    counts["multi_sim_imei"] = len(multi_sim_events)

    # Engine 2: Co-location — case-wide
    co_events = detect_co_location(case_id, db)
    for ev in co_events:
        db.add(ev)
    counts["co_locations"] = len(co_events)

    # Engine 3: Common contacts — case-wide
    cc_events = detect_common_contacts(case_id, db)
    for ev in cc_events:
        db.add(ev)
    counts["common_contacts"] = len(cc_events)

    # Engine 4: Anomaly detection — case-wide
    anomaly_events = detect_anomalies(case_id, db)
    for ev in anomaly_events:
        db.add(ev)
    counts["anomalies"] = len(anomaly_events)

    # Engine 5: OTT fingerprint — per suspect
    for suspect in suspects:
        ott_events = fingerprint_ott(suspect.id, db)
        for ev in ott_events:
            db.add(ev)
        counts["ott_flags"] += len(ott_events)

    # Engine 6: Cross-case handler matcher — case-wide
    xcase_events = detect_cross_case_handlers(case_id, db)
    for ev in xcase_events:
        db.add(ev)
    counts["cross_case_handlers"] = len(xcase_events)

    # Engine 7: Tower silence / last-seen — case-wide
    silence_events = detect_tower_silence(case_id, db)
    for ev in silence_events:
        db.add(ev)
    counts["tower_silence"] = len(silence_events)

    # Engine 8: Night-call burst + loop-call — case-wide
    night_loop_events = detect_night_and_loop_calls(case_id, db)
    for ev in night_loop_events:
        db.add(ev)
    for ev in night_loop_events:
        if ev.event_type == "NIGHT_CALL_BURST":
            counts["night_call_bursts"] += 1
        elif ev.event_type == "LOOP_CALL":
            counts["loop_calls"] += 1

    db.commit()

    total = sum(counts.values())

    # ── Audit Trail: record this analysis run ──────────────────────────────────
    log_audit(
        db=db,
        action_type="ANALYSIS_RUN",
        entity_type="Case",
        entity_id=case_id,
        entity_label=case.name,
        request=request,
        detail={"engines_run": 8, "events_generated": total, "breakdown": counts},
    )

    return AnalysisSummary(events_generated=total, summary=counts)
