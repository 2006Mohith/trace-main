from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Case, Event
from schemas import EventOut

router = APIRouter(tags=["events"])


@router.get("/cases/{case_id}/events", response_model=List[EventOut])
def list_events(
    case_id: str,
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    q = db.query(Event).filter(Event.case_id == case_id)
    if event_type:
        q = q.filter(Event.event_type == event_type.upper())
    if severity:
        q = q.filter(Event.severity == severity.upper())

    events = q.all()
    # Sort: events with occurred_at first (most recent), then nulls last
    events = sorted(events, key=lambda ev: ev.occurred_at or __import__('datetime').datetime.min, reverse=True)
    return [
        EventOut(
            id=ev.id,
            case_id=ev.case_id,
            event_type=ev.event_type,
            severity=ev.severity,
            involved_suspects=ev.involved_suspects or [],
            detail=ev.detail,
            occurred_at=ev.occurred_at,
        )
        for ev in events
    ]
