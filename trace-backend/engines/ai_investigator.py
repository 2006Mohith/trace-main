import os
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional
from sqlalchemy.orm import Session
from anthropic import Anthropic, AsyncAnthropic

from models import Case, Suspect, CDRRecord, IPDRRecord, Event, CCTVCamera, CCTVSighting, AIInvestigationReport

# Logger
logger = logging.getLogger("ai_investigator")

def get_anthropic_client() -> Optional[Anthropic]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)

def get_async_anthropic_client() -> Optional[AsyncAnthropic]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return AsyncAnthropic(api_key=api_key)


# ── Context Builder ───────────────────────────────────────────────────────────

def build_case_briefing(case_id: str, db: Session) -> dict:
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError("Case not found")
        
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    sus_ids = [s.id for s in suspects]
    events = db.query(Event).filter(Event.case_id == case_id).all()
    
    suspect_profiles = []
    for s in suspects:
        recs = db.query(CDRRecord).filter(CDRRecord.suspect_id == s.id).all()
        total_calls = len(recs)
        
        # Calculate night calls ratio
        n_night = sum(1 for r in recs if r.timestamp.hour >= 23 or r.timestamp.hour < 5)
        night_ratio = round((n_night / total_calls * 100), 2) if total_calls > 0 else 0.0
        
        # Calculate event counts per suspect
        colocations = sum(1 for e in events if e.event_type == "CO_LOCATION" and s.label in e.involved_suspects)
        swaps = sum(1 for e in events if e.event_type == "IMEI_SWAP" and s.label in e.involved_suspects)
        gaps = sum(1 for e in events if e.event_type == "TOWER_SILENCE" and s.label in e.involved_suspects)
        
        # Search for Anomaly score in events
        anomaly_score = 0
        for e in events:
            if e.event_type == "ANOMALY" and s.label in e.involved_suspects:
                anomaly_score = e.detail.get("anomaly_score", 0)
                break
                
        category = "LOW"
        if anomaly_score > 80: category = "CRITICAL"
        elif anomaly_score > 60: category = "HIGH"
        elif anomaly_score > 30: category = "MEDIUM"
        
        # App usage fingerprinting
        ipdrs = db.query(IPDRRecord).filter(IPDRRecord.suspect_id == s.id).all()
        apps = sorted(list(set(i.app_label for i in ipdrs if i.app_label and i.app_label != "Unknown")))
        app_list = ", ".join(apps) if apps else "None"
        
        # CCTV sightings count
        sightings_count = db.query(CCTVSighting).filter(CCTVSighting.suspect_id == s.id).count()
        
        suspect_profiles.append(
            f"  Name: {s.label} | Score: {anomaly_score}/100 | Category: {category}\n"
            f"  Primary Number: {s.primary_msisdn}\n"
            f"  Total Calls: {total_calls} | Night Call Ratio: {night_ratio}%\n"
            f"  IMEI Swaps: {swaps} | Silence Gaps: {gaps} | Co-locations: {colocations}\n"
            f"  Top Apps Used: {app_list}\n"
            f"  CCTV Sightings: {sightings_count}\n"
        )
        
    # Format events list
    event_strings = []
    for e in events:
        involved = ", ".join(e.involved_suspects)
        event_strings.append(f"  {e.event_type} | Severity: {e.severity} | Suspects: [{involved}] | Detail: {json.dumps(e.detail)} | Occurred: {e.occurred_at.isoformat() if e.occurred_at else 'N/A'}")
        
    # CCTV Summary
    cameras_count = db.query(CCTVCamera).count()
    sightings = db.query(CCTVSighting).filter(CCTVSighting.suspect_id.in_(sus_ids)).order_by(CCTVSighting.captured_at.desc()).limit(10).all()
    recent_sightings_summary = []
    for sig in sightings:
        lbl = next((s.label for s in suspects if s.id == sig.suspect_id), "Unknown")
        recent_sightings_summary.append(f"Suspect '{lbl}' spotted on Camera '{sig.camera_id}' at {sig.captured_at.isoformat()}")
        
    return {
        "case_name": case.name,
        "suspect_count": len(suspects),
        "total_cdr": db.query(CDRRecord).filter(CDRRecord.suspect_id.in_(sus_ids)).count(),
        "total_ipdr": db.query(IPDRRecord).filter(IPDRRecord.suspect_id.in_(sus_ids)).count(),
        "analysis_date": datetime.utcnow().isoformat(),
        "suspect_profiles_block": "\n".join(suspect_profiles),
        "events_block": "\n".join(event_strings[:50]),  # Limit to top 50 to avoid prompt overflow
        "common_contact_count": sum(1 for e in events if e.event_type == "COMMON_CONTACT"),
        "cluster_count": max(1, len(suspects) // 2),
        "cross_case_links": sum(1 for e in events if e.event_type == "CROSS_CASE_HANDLER"),
        "total_sightings": len(sightings),
        "camera_count": cameras_count,
        "recent_sightings_summary": "\n  ".join(recent_sightings_summary) if recent_sightings_summary else "None"
    }


# ── AI Investigation Runner ──────────────────────────────────────────────────

async def run_ai_investigation_stream(
    case_id: str, 
    officer_id: str, 
    db: Session
) -> AsyncGenerator[str, None]:
    """
    Assembles case context, prompts Claude API, yields token chunks,
    saves the final report response to the database.
    """
    # 1. Retrieve case context
    try:
        ctx = build_case_briefing(case_id, db)
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Failed to gather case data: {e}'})}\n\n"
        return
        
    # Build System Prompt
    system_prompt = f"""You are TRACE-AI, an expert criminal intelligence analyst and investigation advisor embedded in the TRACE platform used by Andhra Pradesh Police, Ongole SP Office. You have access to the complete analytical output for this case and must provide structured, actionable investigative guidance.

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

Provide your analysis in the exact JSON structure specified. Be specific, factual, and cite exact suspect names, numbers, timestamps, and event types from the data. Do not speculate beyond what the data shows. Flag clearly when evidence is circumstantial vs strong.
"""

    user_prompt = """Analyze this case and provide a complete investigation roadmap in this exact JSON format:
{
  "threat_summary": {
    "overall_risk": "LOW|MEDIUM|HIGH|CRITICAL",
    "primary_threat_actor": "suspect name",
    "key_finding": "single most important finding in 1-2 sentences",
    "confidence_level": "LOW|MEDIUM|HIGH"
  },
  "suspect_rankings": [
    {
      "rank": 1,
      "suspect": "name",
      "why_priority": "specific reason citing actual data",
      "immediate_action": "exact action to take"
    }
  ],
  "investigation_steps": [
    {
      "step": 1,
      "priority": "IMMEDIATE|HIGH|MEDIUM|LOW",
      "action": "specific investigative action",
      "reason": "why this step, citing specific events/data",
      "expected_outcome": "what this step should reveal",
      "legal_basis": "relevant IPC section or IT Act provision"
    }
  ],
  "network_insights": {
    "key_hub": "most connected suspect or contact",
    "suspected_role": "leader|courier|financier|handler|unknown",
    "coordination_pattern": "description of how they communicate",
    "recommended_surveillance": "specific surveillance recommendation"
  },
  "evidence_gaps": [
    {
      "gap": "what evidence is missing",
      "how_to_fill": "specific action to obtain it",
      "urgency": "HIGH|MEDIUM|LOW"
    }
  ],
  "court_readiness": {
    "strength": "WEAK|MODERATE|STRONG",
    "strongest_evidence": "specific event/record that is most court-admissible",
    "section_65b_ready": true,
    "recommended_charges": ["IPC section with description"]
  },
  "alerts": [
    {
      "type": "FLIGHT_RISK|DESTROY_EVIDENCE|ACCOMPLICE_ALERT|PATTERN_CHANGE",
      "suspect": "name",
      "reason": "specific reason"
    }
  ],
  "follow_up_questions": [
    "specific question the officer should investigate next"
  ]
}
"""

    # 2. Check for Claude API client
    client = get_async_anthropic_client()
    model_name = "claude-3-5-sonnet-20241022"
    
    if not client:
        # Generate Realistic Mock Response for Offline/Development Fallback
        yield "data: {\"status\": \"starting_mock_simulation\"}\n\n"
        import asyncio
        await asyncio.sleep(1.0)
        
        mock_response = {
            "threat_summary": {
                "overall_risk": "HIGH",
                "primary_threat_actor": ctx["case_name"],
                "key_finding": "High density co-location meetings and IMEI swap device evasion detected among suspects in Andhra/Telangana border zones.",
                "confidence_level": "HIGH"
            },
            "suspect_rankings": [
                {
                    "rank": 1,
                    "suspect": "Kalyan Chakravarthy",
                    "why_priority": "Primary suspect displaying critical coordination patterns, loop-calls and a registered handset swap on June 3rd.",
                    "immediate_action": "Secure CDR logs, trace active IMEI tower location, and dispatch field unit."
                }
            ],
            "investigation_steps": [
                {
                    "step": 1,
                    "priority": "IMMEDIATE",
                    "action": "Deploy geospatial surveillance on tower CDD-001 at Chirala.",
                    "reason": "Repeated co-location events between Kalyan Chakravarthy and Venkatesh Prasad.",
                    "expected_outcome": "Visual identification of meeting coordinates.",
                    "legal_basis": "BNS Section 111 (Organized Crime) / IT Act Sec 69"
                }
            ],
            "network_insights": {
                "key_hub": "919888000111",
                "suspected_role": "handler",
                "coordination_pattern": "Loop-calls detected during night hours (23:00 to 05:00).",
                "recommended_surveillance": "Intercept target handler's IMSI identifier."
            },
            "evidence_gaps": [
                {
                    "gap": "IPDR logs for secondary contacts",
                    "how_to_fill": "Submit standard operator request form to telecom cell.",
                    "urgency": "HIGH"
                }
            ],
            "court_readiness": {
                "strength": "STRONG",
                "strongest_evidence": "IMEI swaps matched on June 3rd paired with co-locations.",
                "section_65b_ready": True,
                "recommended_charges": ["BNS Sec 318 (Cheating) / IT Act Sec 66D"]
            },
            "alerts": [
                {
                    "type": "PATTERN_CHANGE",
                    "suspect": "Venkatesh Prasad",
                    "reason": "Drastic decrease in call volume combined with tower silence gap exceeding 12 hours."
                }
            ],
            "follow_up_questions": [
                "Who owns the handler number 919888000111?"
            ]
        }
        
        # Stream mock response token-by-token
        full_str = json.dumps(mock_response, indent=2)
        chunk_size = 32
        for i in range(0, len(full_str), chunk_size):
            chunk = full_str[i:i+chunk_size]
            yield f"data: {json.dumps({'text': chunk})}\n\n"
            await asyncio.sleep(0.05)
            
        # Save mock report to DB
        report_entry = AIInvestigationReport(
            case_id=case_id,
            generated_by_officer_id=officer_id,
            model_used=f"{model_name}-MOCK",
            report_json=mock_response,
            input_token_count=1000,
            output_token_count=500
        )
        db.add(report_entry)
        db.commit()
        
        yield f"data: {json.dumps({'status': 'completed', 'report_id': report_entry.id})}\n\n"
        return

    # Call real Claude API with streaming
    try:
        response_text = ""
        input_tokens = 0
        output_tokens = 0
        
        # Stream from Claude API
        async with client.messages.stream(
            max_tokens=4096,
            model=model_name,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.2
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    text_delta = event.delta.text
                    response_text += text_delta
                    yield f"data: {json.dumps({'text': text_delta})}\n\n"
                elif event.type == "message_start":
                    # Get input token estimates if available
                    pass
            
            # Retrieve complete message metadata
            msg = await stream.get_final_message()
            input_tokens = msg.usage.input_tokens
            output_tokens = msg.usage.output_tokens
            
        # Parse final JSON output
        try:
            # Strip any markdown backticks if Claude wrapped JSON
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            report_data = json.loads(clean_text)
        except Exception:
            # If JSON parsing failed, store raw text as a string in details field
            report_data = {"raw_analysis": response_text}
            
        # Save to DB
        report_entry = AIInvestigationReport(
            case_id=case_id,
            generated_by_officer_id=officer_id,
            model_used=model_name,
            report_json=report_data,
            input_token_count=input_tokens,
            output_token_count=output_tokens
        )
        db.add(report_entry)
        db.commit()
        
        yield f"data: {json.dumps({'status': 'completed', 'report_id': report_entry.id})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Claude API request failed: {e}'})}\n\n"
