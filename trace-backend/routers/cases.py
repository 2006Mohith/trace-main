from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from database import get_db
from models import Case, Suspect, Event
from schemas import CaseCreate, CaseOut

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseOut, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    case = Case(name=payload.name)
    db.add(case)
    db.commit()
    db.refresh(case)
    return CaseOut(
        id=case.id,
        name=case.name,
        created_at=case.created_at,
        suspect_count=0,
        event_count=0,
    )


@router.get("", response_model=List[CaseOut])
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(Case).order_by(Case.created_at.desc()).all()
    result = []
    for c in cases:
        sc = db.query(func.count(Suspect.id)).filter(Suspect.case_id == c.id).scalar()
        ec = db.query(func.count(Event.id)).filter(Event.case_id == c.id).scalar()
        result.append(CaseOut(
            id=c.id,
            name=c.name,
            created_at=c.created_at,
            suspect_count=sc or 0,
            event_count=ec or 0,
        ))
    return result


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    sc = db.query(func.count(Suspect.id)).filter(Suspect.case_id == case.id).scalar()
    ec = db.query(func.count(Event.id)).filter(Event.case_id == case.id).scalar()
    return CaseOut(
        id=case.id,
        name=case.name,
        created_at=case.created_at,
        suspect_count=sc or 0,
        event_count=ec or 0,
    )


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(case)
    db.commit()
    return None

