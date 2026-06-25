import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from database import get_db
from models import AIInvestigationReport, AIChatSession, Case
from auth.rbac import require_permission
from engines.ai_investigator import run_ai_investigation_stream
from engines.ai_chat import ask_investigator
from security.audit_logger import log_audit_enhanced

router = APIRouter(prefix="/ai", tags=["ai"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    question: str


# ── API Endpoints ──────────────────────────────────────────────────────────────

@router.post("/analyze/{case_id}")
async def analyze_case(
    case_id: str,
    request: Request,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    # Verify case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    officer_id = current_officer.get("officer_id")
    
    # Return Server Sent Events (SSE) stream
    # Generates a JSON intelligence report
    generator = run_ai_investigation_stream(case_id, officer_id, db)
    return EventSourceResponse(generator)


@router.get("/report/{case_id}")
def get_latest_report(
    case_id: str,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    # Verify case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    report = (
        db.query(AIInvestigationReport)
        .filter(AIInvestigationReport.case_id == case_id)
        .order_by(AIInvestigationReport.generated_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="No AI investigation report generated for this case yet.")
        
    return {
        "id": report.id,
        "case_id": report.case_id,
        "generated_at": report.generated_at.isoformat() + "Z",
        "generated_by_officer_id": report.generated_by_officer_id,
        "model_used": report.model_used,
        "report_json": report.report_json,
        "input_token_count": report.input_token_count,
        "output_token_count": report.output_token_count
    }


@router.post("/chat/{case_id}")
async def chat_with_ai(
    case_id: str,
    payload: ChatRequest,
    request: Request,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    # Verify case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    session_id = payload.session_id.strip() if payload.session_id else str(uuid.uuid4())
    officer_id = current_officer.get("officer_id")
    question = payload.question.strip()
    
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty")
        
    # Return Server Sent Events (SSE) stream
    generator = ask_investigator(case_id, officer_id, session_id, question, db)
    return EventSourceResponse(generator)


@router.get("/chat/{case_id}/history")
def get_chat_history(
    case_id: str,
    session_id: Optional[str] = None,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    # If no session_id is provided, get the most recent session for this officer & case
    officer_id = current_officer.get("officer_id")
    
    query = db.query(AIChatSession).filter(
        AIChatSession.case_id == case_id,
        AIChatSession.officer_id == officer_id
    )
    
    if session_id:
        query = query.filter(AIChatSession.id == session_id.strip())
        
    session = query.order_by(AIChatSession.started_at.desc()).first()
    if not session:
        return {"session_id": session_id or str(uuid.uuid4()), "messages": []}
        
    return {
        "session_id": session.id,
        "case_id": session.case_id,
        "officer_id": session.officer_id,
        "started_at": session.started_at.isoformat() + "Z",
        "messages": session.messages
    }


@router.delete("/chat/{session_id}")
def clear_chat_session(
    session_id: str,
    request: Request,
    current_officer: dict = Depends(require_permission()),
    db: Session = Depends(get_db)
):
    session = db.query(AIChatSession).filter(AIChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    # Verify ownership
    if session.officer_id != current_officer.get("officer_id") and current_officer.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Unauthorized to delete this session")
        
    db.delete(session)
    db.commit()
    
    log_audit_enhanced(
        db=db,
        action_type="AI_CHAT_DELETE",
        entity_type="ChatSession",
        entity_id=session_id,
        request=request
    )
    
    return {"status": "ok", "message": "Chat session cleared successfully"}
