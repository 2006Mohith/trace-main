"""
Engine 9: Radial Search & Cell Tower Buffer Zones

Given a crime-scene (or any point of interest) latitude, longitude and a
radius in km, this engine uses the Haversine formula to find all CDR records
where the serving cell tower falls within the defined buffer zone during an
optional time window.

Returned as a structured dict (not an Event) — exposed via a dedicated API
endpoint POST /cases/{case_id}/radial-search
"""
import math
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from models import CDRRecord, Suspect


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns great-circle distance in km between two lat/lon points."""
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def radial_search(
    case_id: str,
    db: Session,
    center_lat: float,
    center_lon: float,
    radius_km: float,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Searches all CDR records in the case for tower pings within radius_km
    of (center_lat, center_lon), optionally constrained to a time window.

    Returns:
        {
            "query": { center_lat, center_lon, radius_km, start_time, end_time },
            "hits": [
                {
                    "suspect_id": str,
                    "suspect_label": str,
                    "msisdn": str,
                    "tower_id": str,
                    "tower_lat": float,
                    "tower_lon": float,
                    "distance_km": float,
                    "timestamp": str (ISO),
                    "call_type": str,
                }
            ],
            "suspects_found": [str],   # unique suspect labels
            "total_hits": int,
        }
    """
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()

    hits: List[Dict] = []
    seen_suspects: set = set()

    for suspect in suspects:
        query = (
            db.query(CDRRecord)
            .filter(
                CDRRecord.suspect_id == suspect.id,
                CDRRecord.tower_lat.isnot(None),
                CDRRecord.tower_lon.isnot(None),
            )
        )
        if start_time:
            query = query.filter(CDRRecord.timestamp >= start_time)
        if end_time:
            query = query.filter(CDRRecord.timestamp <= end_time)

        records = query.order_by(CDRRecord.timestamp).all()

        for rec in records:
            dist = haversine_km(center_lat, center_lon, rec.tower_lat, rec.tower_lon)
            if dist <= radius_km:
                hits.append({
                    "suspect_id": suspect.id,
                    "suspect_label": suspect.label,
                    "msisdn": rec.msisdn_a,
                    "tower_id": rec.tower_id or "UNKNOWN",
                    "tower_lat": rec.tower_lat,
                    "tower_lon": rec.tower_lon,
                    "distance_km": round(dist, 3),
                    "timestamp": rec.timestamp.isoformat(),
                    "call_type": rec.call_type or "UNKNOWN",
                    "duration_sec": rec.duration_sec,
                })
                seen_suspects.add(suspect.label)

    # Sort hits by distance then timestamp
    hits.sort(key=lambda h: (h["distance_km"], h["timestamp"]))

    return {
        "query": {
            "center_lat": center_lat,
            "center_lon": center_lon,
            "radius_km": radius_km,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
        },
        "hits": hits,
        "suspects_found": sorted(list(seen_suspects)),
        "total_hits": len(hits),
    }
