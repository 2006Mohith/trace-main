import os
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional
from sqlalchemy.orm import Session
from anthropic import AsyncAnthropic

from models import AIChatSession
from engines.ai_investigator import build_case_briefing, get_async_anthropic_client
from security.audit_logger import log_audit_enhanced

logger = logging.getLogger("ai_chat")

async def ask_investigator(
    case_id: str,
    officer_id: str,
    session_id: str,
    question: str,
    db: Session
) -> AsyncGenerator[str, None]:
    """
    Continues a chat session, streams the response from Claude,
    saves the updated chat history to the session record in the DB.
    """
    # 1. Fetch or create chat session
    session = db.query(AIChatSession).filter(AIChatSession.id == session_id).first()
    if not session:
        session = AIChatSession(
            id=session_id,
            case_id=case_id,
            officer_id=officer_id,
            messages=[]
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
    messages = list(session.messages) if session.messages else []
    
    # Append the user's message
    user_msg = {
        "role": "user",
        "content": question,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    messages.append(user_msg)
    
    # 2. Build system context from case briefing
    try:
        ctx = build_case_briefing(case_id, db)
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Failed to load case context: {e}'})}\n\n"
        return
        
    system_prompt = f"""You are TRACE-AI, an expert criminal intelligence analyst and investigation advisor embedded in the TRACE platform used by Andhra Pradesh Police, Ongole SP Office. You are assisting an investigating officer in a live Q&A session about the current case.
Refer to the case details below when answering. Be specific, cite names, numbers, and timestamps. Do not speculate or leak information outside of the provided data.

CASE DATA:
Case Name: {ctx['case_name']}
Total Suspects: {ctx['suspect_count']}
Total CDR Records: {ctx['total_cdr']}
Total IPDR Records: {ctx['total_ipdr']}
Analysis Date: {ctx['analysis_date']}

SUSPECT PROFILES:
{ctx['suspect_profiles_block']}

ANALYTICAL EVENTS (sorted by severity):
{ctx['events_block']}

NETWORK INTELLIGENCE:
Common Contacts: {ctx['common_contact_count']}
Network Clusters: {ctx['cluster_count']}
Cross-Case Links: {ctx['cross_case_links']}

CCTV INTELLIGENCE:
Total Sightings: {ctx['total_sightings']}
Cameras Active: {ctx['camera_count']}
Recent Sightings: {ctx['recent_sightings_summary']}
"""

    # Format history for Claude
    # Claude messages API accepts role in ('user', 'assistant') and content as a string
    claude_messages = []
    for msg in messages:
        claude_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
        
    client = get_async_anthropic_client()
    model_name = "claude-3-5-sonnet-20241022"
    
    if not client:
        # Development/Offline mock response stream
        yield "data: {\"status\": \"starting_chat_mock\"}\n\n"
        import asyncio
        await asyncio.sleep(0.5)
        
        # Simple dynamic mock responses based on queries
        q_lower = question.lower()
        if "mastermind" in q_lower or "leader" in q_lower:
            response_text = f"Based on the call network logs, Kalyan Chakravarthy is the highly central suspect with an anomaly score of 72/100, executing IMEI swaps and repeating night call loops. He is the most probable mastermind."
        elif "silence" in q_lower or "last seen" in q_lower:
            response_text = f"Venkatesh Prasad displays critical radio-silence gaps exceeding 12 hours. This suggests device switch-off to evade tracing during transit."
        elif "arrest" in q_lower or "warrant" in q_lower:
            response_text = f"I recommend targeting Kalyan Chakravarthy first. The combination of IMEI swaps on June 3rd and repeated co-locations at Chirala tower with Venkatesh Prasad provides strong court-admissible forensic linkages."
        else:
            response_text = f"I have processed your query: '{question}'. Looking at the TRACE intelligence ledger, we have {ctx['suspect_count']} suspects and {ctx['total_cdr']} call records under monitoring in case '{ctx['case_name']}'. How can I help you investigate these links further?"
            
        chunk_size = 8
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i+chunk_size]
            yield f"data: {json.dumps({'text': chunk})}\n\n"
            await asyncio.sleep(0.05)
            
        # Save assistant message to history
        assistant_msg = {
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        messages.append(assistant_msg)
        
        session.messages = messages
        db.commit()
        
        # Log AI_QUERY audit event
        log_audit_enhanced(
            db=db,
            action_type="AI_QUERY",
            entity_type="ChatSession",
            entity_id=session_id,
            detail={"question": question, "mock": True},
            officer_id=officer_id
        )
        
        yield f"data: {json.dumps({'status': 'completed'})}\n\n"
        return
        
    # Real Claude API call
    try:
        response_text = ""
        input_tokens = 0
        output_tokens = 0
        
        async with client.messages.stream(
            max_tokens=2048,
            model=model_name,
            system=system_prompt,
            messages=claude_messages,
            temperature=0.2
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    text_delta = event.delta.text
                    response_text += text_delta
                    yield f"data: {json.dumps({'text': text_delta})}\n\n"
            
            msg = await stream.get_final_message()
            input_tokens = msg.usage.input_tokens
            output_tokens = msg.usage.output_tokens
            
        # Save assistant message to history
        assistant_msg = {
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        messages.append(assistant_msg)
        
        session.messages = messages
        db.commit()
        
        # Log AI_QUERY audit event with token usage
        log_audit_enhanced(
            db=db,
            action_type="AI_QUERY",
            entity_type="ChatSession",
            entity_id=session_id,
            detail={
                "question": question,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            },
            officer_id=officer_id
        )
        
        yield f"data: {json.dumps({'status': 'completed'})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Claude chat request failed: {e}'})}\n\n"
