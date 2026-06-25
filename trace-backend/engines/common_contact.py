"""
Engine 3: Common Contact Detection
Finds phone numbers that appear in multiple suspects' CDR records.
"""
from typing import List
from collections import defaultdict
import uuid
from sqlalchemy.orm import Session
from models import CDRRecord, Suspect, Event


def detect_common_contacts(
    case_id: str,
    db: Session,
    min_suspects: int = 2,
) -> List[Event]:
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    if len(suspects) < min_suspects:
        return []

    # For each suspect, get the set of all numbers they contacted
    suspect_contacts: dict = {}  # label -> set of msisdn_b
    contact_call_counts: dict = {}  # (label, msisdn_b) -> count

    for suspect in suspects:
        recs = db.query(CDRRecord).filter(CDRRecord.suspect_id == suspect.id).all()
        contact_set = set()
        for r in recs:
            contact_set.add(r.msisdn_b)
            key = (suspect.label, r.msisdn_b)
            contact_call_counts[key] = contact_call_counts.get(key, 0) + 1
        # Also include incoming (msisdn_a was them, but also where msisdn_b == their number from others)
        suspect_contacts[suspect.label] = contact_set

    # Find numbers that appear in 2+ suspects
    number_to_suspects: dict = defaultdict(list)
    for label, contacts in suspect_contacts.items():
        for number in contacts:
            # Exclude the suspects' own primary numbers
            own_numbers = {s.primary_msisdn for s in suspects}
            if number not in own_numbers:
                number_to_suspects[number].append(label)

    events: List[Event] = []
    for number, labels in number_to_suspects.items():
        unique_labels = list(set(labels))
        if len(unique_labels) < min_suspects:
            continue

        total_calls = sum(
            contact_call_counts.get((label, number), 0) for label in unique_labels
        )
        severity = "HIGH" if len(unique_labels) >= 3 else "MEDIUM"

        events.append(Event(
            id=str(uuid.uuid4()),
            case_id=case_id,
            event_type="COMMON_CONTACT",
            severity=severity,
            involved_suspects=unique_labels,
            detail={
                "common_number": number,
                "found_in_suspects": unique_labels,
                "total_call_count": total_calls,
            },
            occurred_at=None,
        ))

    # Sort by number of suspects descending
    events.sort(key=lambda e: len(e.involved_suspects), reverse=True)
    return events
