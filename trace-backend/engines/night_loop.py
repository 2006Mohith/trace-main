"""
Engine 8: Night-Call Burst & Loop-Call Aggregation

Two detectors in one engine:

1. NIGHT_CALL_BURST — Detects suspects making an unusually high number of
   calls during the 23:00–05:00 window on any single day. Threshold: >= 5 calls
   in one night window. Criminal significance: coordination before/after crimes.

2. LOOP_CALL — Detects when the same A→B pair makes 3+ calls within a
   30-minute window. Criminal significance: urgent coordination, alarm signals,
   or target confirmation patterns used by criminal networks.
"""
from typing import List
import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from models import CDRRecord, Suspect, Event

NIGHT_START_HOUR = 23
NIGHT_END_HOUR = 5     # exclusive, wraps midnight
NIGHT_CALL_THRESHOLD = 5   # minimum calls in one night to flag

LOOP_WINDOW_MINUTES = 30
LOOP_MIN_CALLS = 3


def detect_night_and_loop_calls(case_id: str, db: Session) -> List[Event]:
    events: List[Event] = []

    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()

    for suspect in suspects:
        records = (
            db.query(CDRRecord)
            .filter(CDRRecord.suspect_id == suspect.id, CDRRecord.call_type == "CALL")
            .order_by(CDRRecord.timestamp)
            .all()
        )

        if not records:
            continue

        # ── NIGHT-CALL BURST DETECTION ────────────────────────────────────────
        # Group calls by calendar night (night starting on date D = calls from
        # D 23:00 through D+1 05:00)
        night_buckets: dict = defaultdict(list)
        for rec in records:
            h = rec.timestamp.hour
            is_night = (h >= NIGHT_START_HOUR) or (h < NIGHT_END_HOUR)
            if not is_night:
                continue
            # Night label: the calendar date of the 23:xx call (or prev date for 00–05)
            if h < NIGHT_END_HOUR:
                night_date = (rec.timestamp - timedelta(days=1)).date()
            else:
                night_date = rec.timestamp.date()
            night_buckets[night_date].append(rec)

        for night_date, night_recs in night_buckets.items():
            if len(night_recs) < NIGHT_CALL_THRESHOLD:
                continue
            unique_contacts = list({r.msisdn_b for r in night_recs})
            first_ts = min(r.timestamp for r in night_recs)
            events.append(Event(
                id=str(uuid.uuid4()),
                case_id=case_id,
                event_type="NIGHT_CALL_BURST",
                severity="MEDIUM",
                involved_suspects=[suspect.label],
                detail={
                    "msisdn": suspect.primary_msisdn,
                    "night_date": str(night_date),
                    "call_count": len(night_recs),
                    "unique_contacts": unique_contacts[:10],  # top 10
                    "window": f"{NIGHT_START_HOUR}:00 – 0{NIGHT_END_HOUR}:00",
                    "note": (
                        f"{len(night_recs)} calls made in the night window of {night_date} "
                        f"— unusual nocturnal activity, possible coordination event."
                    ),
                },
                occurred_at=first_ts,
            ))

        # ── LOOP-CALL DETECTION ───────────────────────────────────────────────
        # Group by (msisdn_a, msisdn_b) pair and find 3+ calls within 30 min
        pair_calls: dict = defaultdict(list)
        for rec in records:
            key = (rec.msisdn_a, rec.msisdn_b)
            pair_calls[key].append(rec)

        emitted_loop_keys: set = set()

        for (msisdn_a, msisdn_b), pair_recs in pair_calls.items():
            if len(pair_recs) < LOOP_MIN_CALLS:
                continue
            sorted_pair = sorted(pair_recs, key=lambda r: r.timestamp)

            # Sliding window
            for i in range(len(sorted_pair) - LOOP_MIN_CALLS + 1):
                window = sorted_pair[i: i + LOOP_MIN_CALLS]
                span = (window[-1].timestamp - window[0].timestamp).total_seconds() / 60
                if span <= LOOP_WINDOW_MINUTES:
                    loop_key = (msisdn_a, msisdn_b, window[0].timestamp.date())
                    if loop_key in emitted_loop_keys:
                        continue
                    emitted_loop_keys.add(loop_key)
                    events.append(Event(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        event_type="LOOP_CALL",
                        severity="HIGH",
                        involved_suspects=[suspect.label],
                        detail={
                            "msisdn_a": msisdn_a,
                            "msisdn_b": msisdn_b,
                            "call_count_in_window": len(window),
                            "window_minutes": round(span, 1),
                            "first_call_at": window[0].timestamp.isoformat(),
                            "last_call_at": window[-1].timestamp.isoformat(),
                            "note": (
                                f"{len(window)} calls from {msisdn_a} → {msisdn_b} "
                                f"within {round(span, 1)} minutes — loop-call / coordination signal."
                            ),
                        },
                        occurred_at=window[0].timestamp,
                    ))
                    break  # one event per pair per day

    return events
