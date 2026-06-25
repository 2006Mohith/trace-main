"""
Engine 5: OTT App Fingerprinting
Resolves dest_ip to organization name and maps to OTT labels.
Uses a local ASN/IP cache; falls back to ipwhois with try/except.
"""
from typing import List, Dict, Optional
import uuid
from sqlalchemy.orm import Session
from models import IPDRRecord, Suspect, Event

# ── Local IP prefix → OTT label cache ─────────────────────────────────────────
# Based on well-known public IP ranges. Used first before any network call.
LOCAL_IP_PREFIX_MAP: Dict[str, str] = {
    # WhatsApp / Meta
    "157.240.": "WhatsApp / Instagram",
    "31.13.": "WhatsApp / Instagram",
    "69.63.": "WhatsApp / Instagram",
    "66.220.": "WhatsApp / Instagram",
    "173.252.": "WhatsApp / Instagram",
    "31.13.24.": "WhatsApp / Instagram",
    # Telegram
    "149.154.": "Telegram",
    "91.108.": "Telegram",
    "95.161.": "Telegram",
    # Google
    "142.250.": "Google Services (Meet / Gmail)",
    "172.217.": "Google Services (Meet / Gmail)",
    "216.58.": "Google Services (Meet / Gmail)",
    "74.125.": "Google Services (Meet / Gmail)",
    "8.8.": "Google Services (Meet / Gmail)",
    # Microsoft
    "13.107.": "Microsoft Teams / Outlook",
    "52.112.": "Microsoft Teams / Outlook",
    "40.96.": "Microsoft Teams / Outlook",
    # Twitter / X
    "104.244.": "X (Twitter)",
    "192.133.": "X (Twitter)",
    # AWS
    "52.": "AWS / Cloud Infrastructure",
    "54.": "AWS / Cloud Infrastructure",
    "3.": "AWS / Cloud Infrastructure",
}

# OTT labels that represent encrypted messaging apps (trigger events)
ENCRYPTED_OTT_APPS = {"WhatsApp / Instagram", "Telegram"}

# In-memory cache for ipwhois results
_ipwhois_cache: Dict[str, str] = {}


def _resolve_org(ip: str) -> str:
    """Resolve an IP to an organization/OTT label using local cache first."""
    # Try local prefix map
    for prefix, label in LOCAL_IP_PREFIX_MAP.items():
        if ip.startswith(prefix):
            return label

    # Check in-memory cache
    if ip in _ipwhois_cache:
        return _ipwhois_cache[ip]

    # Try ipwhois as fallback
    try:
        from ipwhois import IPWhois
        obj = IPWhois(ip)
        result = obj.lookup_rdap(depth=1)
        org = result.get("network", {}).get("name", "") or ""
        org_upper = org.upper()
    except Exception:
        org_upper = ""

    label = _map_org_to_label(org_upper)
    _ipwhois_cache[ip] = label
    return label


def _map_org_to_label(org_upper: str) -> str:
    """Map organization name to OTT label."""
    if "META" in org_upper or "FACEBOOK" in org_upper:
        return "WhatsApp / Instagram"
    if "GOOGLE" in org_upper:
        return "Google Services (Meet / Gmail)"
    if "TELEGRAM" in org_upper:
        return "Telegram"
    if "MICROSOFT" in org_upper:
        return "Microsoft Teams / Outlook"
    if "TWITTER" in org_upper or "X CORP" in org_upper:
        return "X (Twitter)"
    if "AMAZON" in org_upper or "AWS" in org_upper:
        return "AWS / Cloud Infrastructure"
    return "Unknown / Other"


def fingerprint_ott(suspect_id: str, db: Session) -> List[Event]:
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        return []

    ipdrs = db.query(IPDRRecord).filter(IPDRRecord.suspect_id == suspect_id).all()
    if not ipdrs:
        return []

    # Resolve each record and update app_label
    app_groups: Dict[str, list] = {}
    for rec in ipdrs:
        label = _resolve_org(rec.dest_ip)
        rec.app_label = label
        if label not in app_groups:
            app_groups[label] = []
        app_groups[label].append(rec)

    db.flush()

    events: List[Event] = []
    for app, recs in app_groups.items():
        if app not in ENCRYPTED_OTT_APPS:
            continue

        timestamps = [r.timestamp for r in recs]
        total_data = sum(r.data_volume_kb or 0 for r in recs)

        events.append(Event(
            id=str(uuid.uuid4()),
            case_id=suspect.case_id,
            event_type="OTT_USAGE",
            severity="MEDIUM",
            involved_suspects=[suspect.label],
            detail={
                "app": app,
                "session_count": len(recs),
                "total_data_kb": round(total_data, 2),
                "first_seen": min(timestamps).isoformat() if timestamps else None,
                "last_seen": max(timestamps).isoformat() if timestamps else None,
                "date_range": f"{min(timestamps).date()} to {max(timestamps).date()}" if timestamps else "N/A",
            },
            occurred_at=min(timestamps) if timestamps else None,
        ))

    return events
