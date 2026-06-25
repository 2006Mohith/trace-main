"""
Engine 6: Cross-Case Handler Matcher

Finds phone numbers that appear in the CDR records of suspects across
multiple distinct cases. These numbers are probable handler/coordinator
contacts for an organized criminal network spanning different investigations.

Emits one CROSS_CASE_HANDLER event per offending number.
"""
from typing import List
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import CDRRecord, Suspect, Event


def detect_cross_case_handlers(case_id: str, db: Session) -> List[Event]:
    """
    Scans all CDR records globally (across all cases) and finds numbers
    that appear in 2+ different cases. Then emits CROSS_CASE_HANDLER events
    for suspects in the current case that called such a number.
    """
    # Step 1: Find numbers that appear in 2+ cases globally
    results = (
        db.query(CDRRecord.msisdn_b, Suspect.case_id, func.count(CDRRecord.id).label("cnt"))
        .join(Suspect, CDRRecord.suspect_id == Suspect.id)
        .filter(CDRRecord.msisdn_b.isnot(None))
        .group_by(CDRRecord.msisdn_b, Suspect.case_id)
        .all()
    )

    # number -> set of case_ids
    number_to_cases: dict = {}
    number_total_calls: dict = {}
    for msisdn_b, cid, cnt in results:
        if not msisdn_b:
            continue
        if msisdn_b not in number_to_cases:
            number_to_cases[msisdn_b] = set()
            number_total_calls[msisdn_b] = 0
        number_to_cases[msisdn_b].add(cid)
        number_total_calls[msisdn_b] += cnt

    # Keep only numbers that appear in 2+ cases
    handler_numbers = {
        num for num, cases in number_to_cases.items() if len(cases) >= 2
    }

    if not handler_numbers:
        return []

    # Step 2: Find which suspects in THIS case called a handler number
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()

    events: List[Event] = []
    emitted_numbers: set = set()  # one event per handler number per case

    for suspect in suspects:
        cdrs = (
            db.query(CDRRecord)
            .filter(CDRRecord.suspect_id == suspect.id)
            .all()
        )
        for rec in cdrs:
            num = rec.msisdn_b
            if num not in handler_numbers:
                continue
            if num in emitted_numbers:
                continue

            linked_cases = sorted(list(number_to_cases[num]))
            emitted_numbers.add(num)

            events.append(Event(
                id=str(uuid.uuid4()),
                case_id=case_id,
                event_type="CROSS_CASE_HANDLER",
                severity="HIGH",
                involved_suspects=[suspect.label],
                detail={
                    "handler_number": num,
                    "linked_case_ids": linked_cases,
                    "case_count": len(linked_cases),
                    "total_calls_across_cases": number_total_calls[num],
                    "first_contact_timestamp": rec.timestamp.isoformat(),
                    "note": (
                        f"Number {num} appears across {len(linked_cases)} different cases — "
                        "likely a handler or coordinator for an organized criminal network"
                    ),
                },
                occurred_at=rec.timestamp,
            ))

    return events
