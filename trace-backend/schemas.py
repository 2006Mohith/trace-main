from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel


# ── Cases ──────────────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    name: str


class CaseOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    suspect_count: int = 0
    event_count: int = 0

    model_config = {"from_attributes": True}


# ── Suspects ───────────────────────────────────────────────────────────────────

class SuspectOut(BaseModel):
    id: str
    case_id: str
    label: str
    primary_msisdn: str
    anomaly_score: Optional[float] = None
    event_count: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Upload ─────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    suspect_id: str
    rows_inserted_cdr: int
    rows_inserted_ipdr: int


# ── Events ─────────────────────────────────────────────────────────────────────

class EventOut(BaseModel):
    id: str
    case_id: str
    event_type: str
    severity: str
    involved_suspects: List[str]
    detail: Dict[str, Any]
    occurred_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Analysis ───────────────────────────────────────────────────────────────────

class AnalysisSummary(BaseModel):
    events_generated: int
    summary: Dict[str, int]


# ── Network Graph ──────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    node_type: str           # "suspect" | "contact"
    suspect_id: Optional[str] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    call_count: int
    total_duration_sec: int


class NetworkGraphOut(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ── CDR / IPDR summaries ───────────────────────────────────────────────────────

class CDRSummary(BaseModel):
    total_calls: int
    total_sms: int
    unique_contacts: int
    avg_duration_sec: float
    night_call_ratio: float
    burst_score: float
    anomaly_score: Optional[float] = None


class OTTUsageRow(BaseModel):
    app: str
    session_count: int
    total_data_kb: float
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]


class IPDRSummary(BaseModel):
    total_sessions: int
    total_data_kb: float
    ott_breakdown: List[OTTUsageRow]


# ── Suspect Profile ────────────────────────────────────────────────────────────

class MovementPoint(BaseModel):
    tower_id: str
    lat: float
    lon: float
    timestamp: datetime
    co_location: bool = False
    co_location_with: List[str] = []


class CallHeatmapRow(BaseModel):
    hour_of_day: int
    day_of_week: int
    call_count: int


class SuspectProfileOut(BaseModel):
    suspect: SuspectOut
    cdr_summary: Optional[CDRSummary] = None
    ipdr_summary: Optional[IPDRSummary] = None
    events: List[EventOut] = []
    call_heatmap_data: List[CallHeatmapRow] = []
    movement_data: List[MovementPoint] = []
