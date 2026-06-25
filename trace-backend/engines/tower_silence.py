"""
Engine 7: Tower Switch-Off / Last-Seen Analysis

Detects when a suspect goes radio-silent (no CDR activity for >= SILENCE_HOURS)
and records the last known cell tower before the silence gap.

Criminal significance: Suspects often switch off phones around crime events
to evade location tracking. This engine flags those windows.

Emits TOWER_SILENCE events.
"""
from typing import List
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import CDRRecord, Suspect, Event

# Minimum gap (in hours) to be considered a silence window
SILENCE_THRESHOLD_HOURS = 6


def detect_tower_silence(case_id: str, db: Session) -> List[Event]:
    """
    For each suspect in a case, sorts their CDR records by timestamp and
    finds gaps >= SILENCE_THRESHOLD_HOURS. Emits one event per silence window
    with the last known tower before the gap and the tower when they returned.
    """
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    events: List[Event] = []

    for suspect in suspects:
        records = (
            db.query(CDRRecord)
            .filter(CDRRecord.suspect_id == suspect.id)
            .order_by(CDRRecord.timestamp)
            .all()
        )

        if len(records) < 2:
            continue

        for i in range(len(records) - 1):
            curr = records[i]
            nxt = records[i + 1]

            gap = nxt.timestamp - curr.timestamp
            gap_hours = gap.total_seconds() / 3600

            if gap_hours < SILENCE_THRESHOLD_HOURS:
                continue

            # Determine last-seen tower info
            last_tower_id = curr.tower_id or "UNKNOWN"
            last_tower_lat = curr.tower_lat
            last_tower_lon = curr.tower_lon

            # Return tower info
            return_tower_id = nxt.tower_id or "UNKNOWN"

            severity = "HIGH" if gap_hours >= 12 else "MEDIUM"

            events.append(Event(
                id=str(uuid.uuid4()),
                case_id=case_id,
                event_type="TOWER_SILENCE",
                severity=severity,
                involved_suspects=[suspect.label],
                detail={
                    "msisdn": suspect.primary_msisdn,
                    "last_seen_at": curr.timestamp.isoformat(),
                    "last_seen_tower": last_tower_id,
                    "last_seen_lat": last_tower_lat,
                    "last_seen_lon": last_tower_lon,
                    "returned_at": nxt.timestamp.isoformat(),
                    "return_tower": return_tower_id,
                    "gap_hours": round(gap_hours, 2),
                    "note": (
                        f"Phone switched off / no CDR activity for {round(gap_hours, 1)}h. "
                        f"Last seen at tower {last_tower_id}."
                    ),
                },
                occurred_at=curr.timestamp,
            ))

    return events
