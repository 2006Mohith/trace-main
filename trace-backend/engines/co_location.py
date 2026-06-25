"""
Engine 2: Co-location Detection
Finds suspects who appear at the same tower within a time window.
"""
from typing import List
from datetime import datetime, timedelta
import uuid
from sqlalchemy.orm import Session
from models import CDRRecord, Suspect, Event


def detect_co_location(
    case_id: str,
    db: Session,
    time_window_minutes: int = 30,
) -> List[Event]:
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    if len(suspects) < 2:
        return []

    # Collect all tower records per suspect
    suspect_tower_records: dict = {}
    for suspect in suspects:
        recs = (
            db.query(CDRRecord)
            .filter(CDRRecord.suspect_id == suspect.id, CDRRecord.tower_id.isnot(None))
            .order_by(CDRRecord.timestamp)
            .all()
        )
        suspect_tower_records[suspect.label] = recs

    window = timedelta(minutes=time_window_minutes)
    events: List[Event] = []
    dedup_set: set = set()  # (frozenset(suspect_labels), tower_id, window_start_bucket)

    # For each tower, find overlapping windows across suspects
    all_tower_ids = set()
    for recs in suspect_tower_records.values():
        for r in recs:
            if r.tower_id:
                all_tower_ids.add(r.tower_id)

    for tower_id in all_tower_ids:
        # Build list of (timestamp, suspect_label, lat, lon) for this tower
        tower_entries = []
        for label, recs in suspect_tower_records.items():
            for r in recs:
                if r.tower_id == tower_id:
                    tower_entries.append({
                        "ts": r.timestamp,
                        "label": label,
                        "lat": r.tower_lat,
                        "lon": r.tower_lon,
                    })

        if not tower_entries:
            continue

        tower_entries.sort(key=lambda x: x["ts"])

        # Sliding window: for each entry, find all entries within window
        for i, anchor in enumerate(tower_entries):
            window_start = anchor["ts"]
            window_end = anchor["ts"] + window

            present = {}
            for entry in tower_entries:
                if window_start <= entry["ts"] <= window_end:
                    lbl = entry["label"]
                    if lbl not in present:
                        present[lbl] = entry

            if len(present) < 2:
                continue

            # Dedup key: same suspects + same tower + within 2 hours
            suspect_set = frozenset(present.keys())
            two_hour_bucket = int(window_start.timestamp() // 7200)
            dedup_key = (suspect_set, tower_id, two_hour_bucket)
            if dedup_key in dedup_set:
                continue
            dedup_set.add(dedup_key)

            severity = "HIGH" if len(present) >= 3 else "MEDIUM"
            sample = next(iter(present.values()))
            events.append(Event(
                id=str(uuid.uuid4()),
                case_id=case_id,
                event_type="CO_LOCATION",
                severity=severity,
                involved_suspects=list(suspect_set),
                detail={
                    "tower_id": tower_id,
                    "tower_lat": sample.get("lat"),
                    "tower_lon": sample.get("lon"),
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "suspects_present": list(suspect_set),
                },
                occurred_at=window_start,
            ))

    return events
