"""
Geo Intelligence Router — Radial Search & Cell Tower Buffer Zones

POST /cases/{case_id}/radial-search
  Body: { center_lat, center_lon, radius_km, start_time?, end_time? }
  Returns all CDR tower pings within radius_km of the given coordinate.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from models import Case
from engines.radial_search import radial_search

router = APIRouter(tags=["geo"])


class RadialSearchRequest(BaseModel):
    center_lat: float = Field(..., description="Latitude of the crime scene / point of interest")
    center_lon: float = Field(..., description="Longitude of the crime scene / point of interest")
    radius_km: float = Field(5.0, gt=0, le=100, description="Search radius in kilometres (max 100)")
    start_time: Optional[datetime] = Field(None, description="Optional start of time window (ISO 8601)")
    end_time: Optional[datetime] = Field(None, description="Optional end of time window (ISO 8601)")


@router.post("/cases/{case_id}/radial-search")
def post_radial_search(
    case_id: str,
    body: RadialSearchRequest,
    db: Session = Depends(get_db),
):
    """
    Search for all CDR tower pings within `radius_km` kilometres of
    (center_lat, center_lon) for all suspects in a case.
    Optionally filter to a time window.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    result = radial_search(
        case_id=case_id,
        db=db,
        center_lat=body.center_lat,
        center_lon=body.center_lon,
        radius_km=body.radius_km,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    return result
