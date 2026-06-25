import os
import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session

from models import AuditLog
from security.encryption import encrypt_searchable_field

# Append-only local log file handler
audit_file_logger = logging.getLogger("audit_file")
audit_file_logger.setLevel(logging.INFO)

if not audit_file_logger.handlers:
    # Append-only JSON Lines logger
    handler = logging.FileHandler("audit.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter('%(message)s'))
    audit_file_logger.addHandler(handler)

def log_audit_enhanced(
    db: Session,
    action_type: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    entity_label: Optional[str] = None,
    request: Optional[Request] = None,
    detail: Optional[dict] = None,
    status: str = "SUCCESS",
    officer_id: Optional[str] = None,
    officer_role: Optional[str] = None
):
    # 1. Extract request details if request object is present
    ip = None
    host = None
    request_id = "N/A"
    
    if request:
        # X-Forwarded-For fallback
        cf_ip = request.headers.get("x-forwarded-for")
        ip = cf_ip.split(",")[0].strip() if cf_ip else (request.client.host if request.client else None)
        host = request.headers.get("host")
        request_id = getattr(request.state, "request_id", "N/A")
        
        # Read officer information from request state if set by auth middleware
        if not officer_id and hasattr(request.state, "officer_id"):
            officer_id = request.state.officer_id
        if not officer_role and hasattr(request.state, "officer_role"):
            officer_role = request.state.officer_role

    # Default values for officer
    officer_id = officer_id or "ANONYMOUS"
    officer_role = officer_role or "NONE"
    detail = detail or {}

    # 2. Save to database (encrypt IP with searchable blind index)
    encrypted_ip = encrypt_searchable_field(ip) if ip else None
    
    db_entry = AuditLog(
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        officer_ip=encrypted_ip,
        officer_host=host,
        detail=detail,
        timestamp=datetime.utcnow()
    )
    
    try:
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
    except Exception as e:
        db.rollback()
        # Fallback to printing error if db fails, but write local file anyway
        print(f"Database audit logging failed: {e}")

    # 3. Write to append-only local JSON lines file
    log_record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
        "officer_id": officer_id,
        "officer_role": officer_role,
        "officer_ip": ip,  # Local file stores the unencrypted IP for quick local system review (secured locally)
        "action_type": action_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_label": entity_label,
        "detail": detail,
        "status": status
    }
    
    audit_file_logger.info(json.dumps(log_record))
    
    return db_entry
