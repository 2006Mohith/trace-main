"""
Audit Trail Router

Records and retrieves activity audit logs for accountability and chain-of-custody.
Every major platform action is logged with IP, timestamp, entity, and details.

GET  /audit/logs            — paginated list of all audit log entries
GET  /audit/logs/{case_id}  — logs filtered to a specific case entity
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
from models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


# ── Helper: log an action ──────────────────────────────────────────────────────

def log_audit(
    db: Session,
    action_type: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    entity_label: Optional[str] = None,
    request: Optional[Request] = None,
    detail: Optional[dict] = None,
):
    """
    Call this from any router to create an audit log entry.
    Example:
        log_audit(db, "ANALYSIS_RUN", "Case", case_id, case.name, request,
                  {"engines_run": 8, "events_generated": 42})
    """
    ip = None
    host = None
    if request:
        # X-Forwarded-For for proxied setups, fallback to direct client
        forwarded = request.headers.get("x-forwarded-for")
        ip = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else None
        host = request.headers.get("host")

    entry = AuditLog(
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        officer_ip=ip,
        officer_host=host,
        detail=detail or {},
        timestamp=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ── API Endpoints ──────────────────────────────────────────────────────────────

@router.get("/logs")
def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    action_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns the most recent audit log entries, newest first.
    Optionally filter by action_type (e.g. ANALYSIS_RUN, REPORT_GENERATED).
    """
    q = db.query(AuditLog)
    if action_type:
        q = q.filter(AuditLog.action_type == action_type)
    total = q.count()
    entries = q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [
            {
                "id": e.id,
                "action_type": e.action_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "entity_label": e.entity_label,
                "officer_ip": e.officer_ip,
                "officer_host": e.officer_host,
                "detail": e.detail,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries
        ],
    }


@router.get("/logs/case/{case_id}")
def get_audit_logs_for_case(
    case_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Returns audit logs for a specific case entity."""
    entries = (
        db.query(AuditLog)
        .filter(AuditLog.entity_id == case_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "action_type": e.action_type,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "entity_label": e.entity_label,
            "officer_ip": e.officer_ip,
            "detail": e.detail,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in entries
    ]
