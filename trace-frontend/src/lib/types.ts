export interface CaseOut {
  id: string;
  name: string;
  created_at: string;
  suspect_count: number;
  event_count: number;
}

export interface SuspectOut {
  id: string;
  case_id: string;
  label: string;
  primary_msisdn: string;
  anomaly_score?: number;
  event_count?: number;
}

export interface UploadResponse {
  suspect_id: string;
  rows_inserted_cdr: number;
  rows_inserted_ipdr: number;
}

export interface EventOut {
  id: string;
  case_id: string;
  event_type: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  involved_suspects: string[];
  detail: Record<string, unknown>;
  occurred_at: string | null;
}

export interface AnalysisSummary {
  events_generated: number;
  summary: {
    imei_swaps: number;
    co_locations: number;
    common_contacts: number;
    anomalies: number;
    ott_flags: number;
  };
}

export interface GraphNode {
  id: string;
  label: string;
  node_type: "suspect" | "contact" | "tower";
  suspect_id?: string;
  tower_name?: string;
  tower_lat?: number;
  tower_lon?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  call_count: number;
  total_duration_sec: number;
  edge_type?: "call" | "handler" | "co_location";
  meeting_label?: string;
}

export interface NetworkGraphOut {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface CDRSummary {
  total_calls: number;
  total_sms: number;
  unique_contacts: number;
  avg_duration_sec: number;
  night_call_ratio: number;
  burst_score: number;
  anomaly_score?: number | null;
}

export interface OTTUsageRow {
  app: string;
  session_count: number;
  total_data_kb: number;
  first_seen: string | null;
  last_seen: string | null;
}

export interface IPDRSummary {
  total_sessions: number;
  total_data_kb: number;
  ott_breakdown: OTTUsageRow[];
}

export interface MovementPoint {
  tower_id: string;
  lat: number;
  lon: number;
  timestamp: string;
  co_location: boolean;
  co_location_with: string[];
}

export interface CallHeatmapRow {
  hour_of_day: number;
  day_of_week: number;
  call_count: number;
}

export interface SuspectProfileOut {
  suspect: SuspectOut;
  cdr_summary: CDRSummary | null;
  ipdr_summary: IPDRSummary | null;
  events: EventOut[];
  call_heatmap_data: CallHeatmapRow[];
  movement_data: MovementPoint[];
}

export interface SharedContact {
  number: string;
  suspects: string[];
  total_calls: number;
  suspect_count: number;
}

