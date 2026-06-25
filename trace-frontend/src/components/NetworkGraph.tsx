import { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import ReactFlow, {
  Background,
  Controls,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import dagre from "@dagrejs/dagre";
import { api } from "../lib/api";
import type { NetworkGraphOut, SuspectOut } from "../lib/types";
import { Maximize2, Minimize2, X, Search } from "lucide-react";

// ── Anomaly score converter ──────────────────────────────────────────────────
function convertAnomalyScore(rawScore: number): number {
  const clamped = Math.max(-0.8, Math.min(0.5, rawScore));
  return Math.round(((clamped - 0.5) / (-0.8 - 0.5)) * 100);
}

// ── Duration Formatter ───────────────────────────────────────────────────────
function formatDuration(seconds: number): string {
  if (seconds <= 0) return "0s";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  
  const parts = [];
  if (h > 0) parts.push(`${h}h`);
  if (m > 0) parts.push(`${m}m`);
  if (s > 0 || parts.length === 0) parts.push(`${s}s`);
  return parts.join(" ");
}

// ── Dagre layout helper ──────────────────────────────────────────────────────
function applyDagreLayout(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 30, ranksep: 80 });

  nodes.forEach((n) => {
    let w = 120;
    let h = 36;
    if (n.type === "suspect" || n.type === "handler" || n.type === "common") { w = 140; h = 38; }
    g.setNode(n.id, { width: w, height: h });
  });
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);

  return nodes.map((n) => {
    const pos = g.node(n.id);
    let w = 120;
    let h = 36;
    if (n.type === "suspect" || n.type === "handler" || n.type === "common") { w = 140; h = 38; }
    return { ...n, position: { x: pos.x - w / 2, y: pos.y - h / 2 } };
  });
}

// ── Custom Node Types ─────────────────────────────────────────────────────────

// Suspect Node: Simple blue rounded pill
function SuspectNode({ data }: NodeProps) {
  const isHighlighted = data.isSearchMatch;
  const isDimmed = data.isSearchActive && !isHighlighted;

  return (
    <div
      style={{
        width: 140,
        height: 38,
        transition: "opacity 0.2s",
        opacity: isDimmed ? 0.35 : 1,
        border: isHighlighted ? "2px solid #06b6d4" : "1.5px solid #2563eb",
      }}
      className="bg-blue-50 text-blue-950 rounded px-2.5 py-1 flex flex-col items-center justify-center font-sans select-none shadow-sm"
    >
      <Handle type="target" position={Position.Left} style={{ background: "#2563eb", width: 5, height: 5 }} />
      <span className="text-[10px] font-bold truncate w-full text-center">{data.label}</span>
      <span className="text-[7px] font-mono text-blue-500/80 truncate w-full text-center">{data.msisdn}</span>
      <Handle type="source" position={Position.Right} style={{ background: "#2563eb", width: 5, height: 5 }} />
    </div>
  );
}

// Handler Node: Simple red rounded pill
function HandlerNode({ data }: NodeProps) {
  const isHighlighted = data.isSearchMatch;
  const isDimmed = data.isSearchActive && !isHighlighted;
  return (
    <div
      style={{
        width: 140,
        height: 38,
        transition: "opacity 0.2s",
        opacity: isDimmed ? 0.35 : 1,
        border: isHighlighted ? "2px solid #06b6d4" : "1.5px solid #dc2626",
      }}
      className="bg-red-50 text-red-950 rounded px-2.5 py-1 flex flex-col items-center justify-center font-sans select-none shadow-sm"
    >
      <Handle type="target" position={Position.Left} style={{ background: "#dc2626", width: 5, height: 5 }} />
      <span className="text-[10px] font-bold truncate w-full text-center">{data.label}</span>
      <span className="text-[7px] font-bold text-red-500 uppercase tracking-wider truncate w-full text-center">HANDLER</span>
      <Handle type="source" position={Position.Right} style={{ background: "#dc2626", width: 5, height: 5 }} />
    </div>
  );
}

// Common Contact Node: Indigo dashed pill
function CommonContactNode({ data }: NodeProps) {
  const isHighlighted = data.isSearchMatch;
  const isDimmed = data.isSearchActive && !isHighlighted;
  return (
    <div
      style={{
        width: 140,
        height: 38,
        transition: "opacity 0.2s",
        opacity: isDimmed ? 0.35 : 1,
        border: isHighlighted ? "2px solid #06b6d4" : "1.5px dashed #6366f1",
      }}
      className="bg-indigo-50 text-indigo-950 rounded px-2.5 py-1 flex flex-col items-center justify-center font-sans select-none shadow-sm"
    >
      <Handle type="target" position={Position.Left} style={{ background: "#6366f1", width: 5, height: 5 }} />
      <span className="text-[10px] font-mono font-medium truncate w-full text-center">{data.label}</span>
      <span className="text-[7px] font-bold text-indigo-500 uppercase tracking-widest truncate w-full text-center">COMMON LINK</span>
      <Handle type="source" position={Position.Right} style={{ background: "#6366f1", width: 5, height: 5 }} />
    </div>
  );
}

// Standard Contact Node: Clean slate pill
function StandardContactNode({ data }: NodeProps) {
  const isHighlighted = data.isSearchMatch;
  const isDimmed = data.isSearchActive && !isHighlighted;
  return (
    <div
      style={{
        width: 120,
        height: 36,
        transition: "opacity 0.2s",
        opacity: isDimmed ? 0.35 : 1,
        border: isHighlighted ? "2px solid #06b6d4" : "1px solid #64748b",
      }}
      className="bg-slate-50 text-slate-800 rounded px-2 py-1 flex flex-col items-center justify-center font-sans select-none shadow-sm"
    >
      <Handle type="target" position={Position.Left} style={{ background: "#64748b", width: 5, height: 5 }} />
      <span className="text-[10px] font-mono font-medium truncate w-full text-center">{data.label}</span>
      <span className="text-[7px] text-slate-400 uppercase tracking-wider truncate w-full text-center">CONTACT</span>
      <Handle type="source" position={Position.Right} style={{ background: "#64748b", width: 5, height: 5 }} />
    </div>
  );
}

// Cell Tower Node: Cyan pill
function TowerNode({ data }: NodeProps) {
  const isHighlighted = data.isSearchMatch;
  const isDimmed = data.isSearchActive && !isHighlighted;
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: 120,
        height: 36,
        transition: "opacity 0.2s",
        opacity: isDimmed ? 0.35 : 1,
        border: isHighlighted ? "2px solid #06b6d4" : "1px solid #0891b2",
      }}
      className="bg-cyan-50 text-cyan-900 rounded px-2 py-1 flex flex-col items-center justify-center font-sans select-none shadow-sm relative"
    >
      <Handle type="target" position={Position.Left} style={{ background: "#0891b2", width: 5, height: 5 }} />
      <span className="text-[9px] font-bold truncate w-full text-center">{data.tower_name}</span>
      <span className="text-[7px] text-cyan-500 uppercase tracking-widest font-semibold truncate w-full text-center">CELL SITE</span>

      {hovered && (
        <div className="absolute top-10 left-1/2 -translate-x-1/2 bg-slate-900 text-slate-300 text-[8px] font-mono p-2 rounded shadow-lg z-50 pointer-events-none min-w-[130px]">
          <div className="text-cyan-400 font-bold mb-0.5">{data.tower_name}</div>
          <div className="text-[7px] text-slate-500">ID: {data.label}</div>
          <div>{data.tower_lat?.toFixed(4)}°N, {data.tower_lon?.toFixed(4)}°E</div>
        </div>
      )}

      <Handle type="source" position={Position.Right} style={{ background: "#0891b2", width: 5, height: 5 }} />
    </div>
  );
}

const nodeTypes = {
  suspect: SuspectNode,
  handler: HandlerNode,
  common: CommonContactNode,
  standard: StandardContactNode,
  tower: TowerNode,
};

// ── Main Component ─────────────────────────────────────────────────────────────

interface Props {
  caseId: string;
  suspects: SuspectOut[];
}

interface SelectedNodeState {
  id: string;
  label: string;
  nodeType: "suspect" | "handler" | "common" | "standard" | "tower";
  msisdn?: string;
  anomalyScore?: number;
  eventCount?: number;
  suspectId?: string;
  totalCalls?: number;
  totalDurationSec?: number;
  callers?: { suspectName: string; callCount: number; durationSec: number }[];
  towerName?: string;
  towerLat?: number;
  towerLon?: number;
  connectedSuspects?: { suspectName: string; callCount: number }[];
}

function NetworkGraphInner({ caseId, suspects }: Props) {
  const { fitView } = useReactFlow();
  const containerRef = useRef<HTMLDivElement>(null);
  const [graphData, setGraphData] = useState<NetworkGraphOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch((err) => {
        console.error("Error attempting to enable fullscreen:", err);
      });
    } else {
      document.exitFullscreen().catch((err) => {
        console.error("Error attempting to exit fullscreen:", err);
      });
    }
  };

  // Toggle states
  const [showTowers, setShowTowers] = useState(false);
  const [showMeetings, setShowMeetings] = useState(true);
  const [callWeight, setCallWeight] = useState(true);
  const [selectedSuspects, setSelectedSuspects] = useState<Set<string>>(new Set());
  const [filterOpen, setFilterOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Side panel
  const [selectedNode, setSelectedNode] = useState<SelectedNodeState | null>(null);
  const [copied, setCopied] = useState(false);
  const filterRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getNetwork(caseId)
      .then(setGraphData)
      .catch(() => setGraphData(null))
      .finally(() => setLoading(false));
  }, [caseId]);

  // Init filter with all suspects
  useEffect(() => {
    if (graphData) {
      const suspectIds = graphData.nodes
        .filter((n) => n.node_type === "suspect")
        .map((n) => n.id);
      setSelectedSuspects(new Set(suspectIds));
    }
  }, [graphData]);

  // Close filter dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(e.target as any)) {
        setFilterOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Sync state and re-fit view on HTML5 fullscreen change
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isNowFullscreen = document.fullscreenElement === containerRef.current;
      setIsFullscreen(isNowFullscreen);
      setTimeout(() => {
        fitView({ duration: 300 });
      }, 150);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, [fitView]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  // Pre-calculate contact types dynamically based on connections
  const contactTypes = new Map<string, "handler" | "common" | "standard">();
  if (graphData) {
    const contactEdges = graphData.edges;
    graphData.nodes.forEach(node => {
      if (node.node_type === "contact") {
        const hasHandlerEdge = contactEdges.some(
          e => e.edge_type === "handler" && (e.source === node.id || e.target === node.id)
        );

        if (hasHandlerEdge) {
          contactTypes.set(node.id, "handler");
        } else {
          const connectedSuspects = new Set<string>();
          contactEdges.forEach(e => {
            if (e.source === node.id || e.target === node.id) {
              const otherId = e.source === node.id ? e.target : e.source;
              const otherNode = graphData.nodes.find(n => n.id === otherId);
              if (otherNode && otherNode.node_type === "suspect") {
                connectedSuspects.add(otherId);
              }
            }
          });
          if (connectedSuspects.size > 1) {
            contactTypes.set(node.id, "common");
          } else {
            contactTypes.set(node.id, "standard");
          }
        }
      }
    });
  }

  const isSearchActive = searchQuery.trim() !== "";

  // Build nodes
  const rawNodes: Node[] = (graphData?.nodes || [])
    .filter((n) => {
      if (n.node_type === "suspect") return selectedSuspects.has(n.id);
      if (n.node_type === "tower" && !showTowers) return false;
      return true;
    })
    .map((n) => {
      const suspectMeta = suspects.find((s) => s.id === n.suspect_id);
      let nodeType: string;
      if (n.node_type === "suspect") {
        nodeType = "suspect";
      } else if (n.node_type === "tower") {
        nodeType = "tower";
      } else {
        nodeType = contactTypes.get(n.id) || "standard";
      }

      return {
        id: n.id,
        type: nodeType,
        position: { x: 0, y: 0 },
        data: {
          label: n.label,
          suspect_id: n.suspect_id,
          node_type: n.node_type,
          msisdn: n.label,
          event_count: suspectMeta?.event_count ?? 0,
          anomaly_score: suspectMeta && suspectMeta.anomaly_score !== undefined ? convertAnomalyScore(suspectMeta.anomaly_score) : 0,
          tower_name: n.tower_name,
          tower_lat: n.tower_lat,
          tower_lon: n.tower_lon,
          isSearchActive,
          isSearchMatch: isSearchActive && (
            n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (n.tower_name && n.tower_name.toLowerCase().includes(searchQuery.toLowerCase()))
          )
        },
      };
    });

  // Build edges
  const rawEdges: Edge[] = (graphData?.edges || [])
    .filter((e) => {
      if (!showMeetings && e.edge_type === "co_location") return false;
      const sourceVisible = rawNodes.some((n) => n.id === e.source);
      const targetVisible = rawNodes.some((n) => n.id === e.target);
      return sourceVisible && targetVisible;
    })
    .map((e, i) => {
      const isHandlerEdge = e.edge_type === "handler";
      const isCoLoc = e.edge_type === "co_location";
      const strokeWidth = callWeight ? Math.max(1.5, e.call_count / 20) : 1.5;

      return {
        id: `edge-${i}`,
        source: e.source,
        target: e.target,
        animated: false,
        label: isCoLoc ? `Met: ${e.meeting_label || "Day 2"}` : undefined,
        style: {
          stroke: isHandlerEdge ? "#dc2626" : isCoLoc ? "#6366f1" : "#94a3b8",
          strokeWidth: isHandlerEdge ? 2 : strokeWidth,
          strokeDasharray: isHandlerEdge ? "5,3" : isCoLoc ? "4,2" : undefined,
          opacity: 0.8,
        },
      };
    });

  // Apply dagre layout dynamically
  const nodes = applyDagreLayout(rawNodes, rawEdges);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const type = node.type as "suspect" | "handler" | "common" | "standard" | "tower";

      if (type === "suspect") {
        setSelectedNode({
          id: node.id,
          label: node.data.label,
          nodeType: type,
          msisdn: node.data.msisdn,
          anomalyScore: node.data.anomaly_score,
          eventCount: node.data.event_count,
          suspectId: node.data.suspect_id,
        });
      } else if (type === "tower") {
        const towerEdges = graphData?.edges.filter(
          (e) => e.target === node.id || e.source === node.id
        ) || [];
        const connectedSuspects = towerEdges.map(e => {
          const otherId = e.source === node.id ? e.target : e.source;
          const suspectObj = suspects.find(s => s.id === otherId);
          return {
            suspectName: suspectObj?.label || "Unknown Suspect",
            callCount: e.call_count
          };
        });

        setSelectedNode({
          id: node.id,
          label: node.data.label,
          nodeType: type,
          towerName: node.data.tower_name,
          towerLat: node.data.tower_lat,
          towerLon: node.data.tower_lon,
          connectedSuspects,
        });
      } else {
        const connectedEdges = graphData?.edges.filter(
          (e) => e.target === node.id || e.source === node.id
        ) || [];

        const totalCalls = connectedEdges.reduce((acc, e) => acc + e.call_count, 0);
        const totalDurationSec = connectedEdges.reduce((acc, e) => acc + e.total_duration_sec, 0);

        const callers = connectedEdges.map((e) => {
          const otherId = e.source === node.id ? e.target : e.source;
          const suspectObj = suspects.find((s) => s.id === otherId);
          return {
            suspectName: suspectObj?.label || "Unknown Caller",
            callCount: e.call_count,
            durationSec: e.total_duration_sec,
          };
        });

        setSelectedNode({
          id: node.id,
          label: node.data.label,
          nodeType: type,
          msisdn: node.data.label,
          totalCalls,
          totalDurationSec,
          callers,
        });
      }
    },
    [graphData, suspects]
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500 text-sm font-sans bg-slate-50">
        Loading case network...
      </div>
    );
  }
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500 text-sm bg-slate-50">
        No network data available. Run analysis first.
      </div>
    );
  }

  const suspectNodes = graphData.nodes.filter((n) => n.node_type === "suspect");

  return (
    <div
      ref={containerRef}
      style={
        isFullscreen
          ? {
              width: "100%",
              height: "100%",
              background: "#f8fafc",
              padding: "16px",
            }
          : {
              width: "100%",
              height: "100%",
              position: "relative",
              background: "#f8fafc",
              overflow: "hidden",
            }
      }
      className="font-sans"
    >
      {/* ── Minimal Toolbar ── */}
      <div className="absolute top-3 left-3 right-3 z-[50] bg-white border border-slate-200 shadow-sm rounded-lg p-2 flex flex-wrap gap-4 items-center justify-between text-slate-700">
        <div className="flex flex-wrap gap-4 items-center">
          <label className="flex items-center gap-2 cursor-pointer select-none text-[11px] font-medium text-slate-600">
            <input
              type="checkbox"
              checked={showTowers}
              onChange={(e) => setShowTowers(e.target.checked)}
              className="w-3.5 h-3.5 accent-blue-600 bg-white border-slate-300 rounded cursor-pointer"
            />
            Towers
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none text-[11px] font-medium text-slate-600">
            <input
              type="checkbox"
              checked={showMeetings}
              onChange={(e) => setShowMeetings(e.target.checked)}
              className="w-3.5 h-3.5 accent-blue-600 bg-white border-slate-300 rounded cursor-pointer"
            />
            Meetings
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none text-[11px] font-medium text-slate-600">
            <input
              type="checkbox"
              checked={callWeight}
              onChange={(e) => setCallWeight(e.target.checked)}
              className="w-3.5 h-3.5 accent-blue-600 bg-white border-slate-300 rounded cursor-pointer"
            />
            Call Weight
          </label>

          <div className="w-px h-4 bg-slate-200" />

          {/* Fit view */}
          <button
            onClick={() => fitView({ duration: 300 })}
            className="flex items-center gap-1 text-[11px] font-medium text-slate-600 hover:text-slate-800 bg-white border border-slate-200 px-2 py-1 rounded transition-colors cursor-pointer"
          >
            <Maximize2 size={11} />
            Fit View
          </button>

          {/* Fullscreen Toggle */}
          <button
            onClick={toggleFullscreen}
            className="flex items-center gap-1 text-[11px] font-medium text-slate-600 hover:text-slate-800 bg-white border border-slate-200 px-2 py-1 rounded transition-colors cursor-pointer"
          >
            {isFullscreen ? <Minimize2 size={11} /> : <Maximize2 size={11} />}
            {isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
          </button>
        </div>

        <div className="flex gap-2 items-center">
          {/* Search Input */}
          <div className="relative flex items-center">
            <Search size={11} className="absolute left-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search MSISDN/Tower..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-white border border-slate-200 rounded pl-7 pr-2.5 py-1 text-[11px] text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 w-44 font-mono"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2 text-slate-400 hover:text-slate-600"
              >
                <X size={10} />
              </button>
            )}
          </div>

          {/* Suspect filter dropdown */}
          <div ref={filterRef} className="relative">
            <button
              onClick={() => setFilterOpen((v) => !v)}
              className="text-[11px] font-medium text-slate-600 hover:text-slate-800 bg-white border border-slate-200 px-2.5 py-1 rounded transition-colors cursor-pointer"
            >
              Targets Selected ▾
            </button>
            {filterOpen && (
              <div className="absolute right-0 top-7 bg-white border border-slate-200 rounded-lg p-2 min-w-[140px] z-50 shadow-md flex flex-col gap-1.5">
                {suspectNodes.map((n) => (
                  <label key={n.id} className="flex items-center gap-2 px-1.5 py-1 hover:bg-slate-50 rounded cursor-pointer text-[11px] text-slate-700">
                    <input
                      type="checkbox"
                      checked={selectedSuspects.has(n.id)}
                      onChange={(e) => {
                        setSelectedSuspects((prev) => {
                          const next = new Set(prev);
                          if (e.target.checked) next.add(n.id);
                          else next.delete(n.id);
                          return next;
                        });
                      }}
                      className="w-3.5 h-3.5 accent-blue-600 bg-white border-slate-300 rounded"
                    />
                    {n.label}
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Legend ── */}
      <div className="absolute bottom-3 left-3 z-[50] bg-white border border-slate-200 rounded-lg p-3 shadow-sm text-[10px] max-w-[170px] text-slate-700">
        <h5 className="font-semibold text-slate-800 mb-2 border-b border-slate-100 pb-1">Legend</h5>
        <div className="flex flex-col gap-2">
          {[
            { color: "border-blue-500 bg-blue-50", label: "Suspect Node" },
            { color: "border-red-600 bg-red-50", label: "Handler Node" },
            { color: "border-dashed border-indigo-500 bg-indigo-50", label: "Common Contact" },
            { color: "border-slate-400 bg-slate-50", label: "Standard Contact" },
            { color: "border-cyan-500 bg-cyan-50", label: "Cell Site" },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-3.5 h-3.5 border rounded-sm ${item.color}`} />
              <span className="text-slate-600 font-mono text-[9px]">{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Minimal Side Panel ── */}
      {selectedNode && (
        <div className="absolute right-0 top-0 bottom-0 w-64 bg-white border-l border-slate-200 z-[60] overflow-y-auto p-4 flex flex-col gap-4 text-slate-800 shadow-md">
          <div className="flex justify-between items-start border-b border-slate-100 pb-3">
            <div>
              <span className="text-[9px] font-mono text-slate-400 uppercase tracking-widest font-bold">
                {selectedNode.nodeType === "tower" ? "Cell Station" : "Target Node"}
              </span>
              <h3 className="text-sm font-bold text-slate-900 mt-0.5">
                {selectedNode.nodeType === "tower" ? selectedNode.towerName : selectedNode.label}
              </h3>
              {selectedNode.msisdn && (
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="text-[10px] font-mono text-slate-500">{selectedNode.msisdn}</span>
                  <button
                    onClick={() => handleCopy(selectedNode.msisdn!)}
                    className="text-[9px] bg-slate-100 text-slate-600 hover:bg-slate-200 px-1.5 py-0.5 rounded font-mono cursor-pointer"
                  >
                    {copied ? "Copied" : "Copy"}
                  </button>
                </div>
              )}
            </div>
            <button 
              onClick={() => setSelectedNode(null)} 
              className="text-slate-400 hover:text-slate-600 p-1 hover:bg-slate-50 rounded-full cursor-pointer"
            >
              <X size={14} />
            </button>
          </div>

          {/* Suspect Specific Content */}
          {selectedNode.nodeType === "suspect" && (
            <div className="flex flex-col gap-3 text-xs">
              {selectedNode.anomalyScore !== undefined && (
                <div>
                  <span className="text-slate-500 font-medium">Anomaly Score:</span>{" "}
                  <span className="font-bold text-slate-900 font-mono">{selectedNode.anomalyScore}/100</span>
                </div>
              )}

              {selectedNode.eventCount !== undefined && (
                <div>
                  <span className="text-slate-500 font-medium">Alert Events:</span>{" "}
                  <span className="font-bold text-slate-900 font-mono">{selectedNode.eventCount}</span>
                </div>
              )}

              {selectedNode.suspectId && (
                <Link
                  to={`/suspects/${selectedNode.suspectId}`}
                  className="mt-2 block text-center py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold shadow transition-colors"
                >
                  View profile →
                </Link>
              )}
            </div>
          )}

          {/* Contact Specific Content */}
          {selectedNode.nodeType !== "suspect" && selectedNode.nodeType !== "tower" && (
            <div className="flex flex-col gap-3 text-xs">
              <div>
                <span className="text-slate-500 font-medium">Total Calls:</span>{" "}
                <span className="font-bold text-slate-900 font-mono">{selectedNode.totalCalls}</span>
              </div>
              <div>
                <span className="text-slate-500 font-medium">Duration:</span>{" "}
                <span className="font-bold text-slate-900 font-mono">{formatDuration(selectedNode.totalDurationSec || 0)}</span>
              </div>

              <div className="border-t border-slate-100 pt-3">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2 block">Callers</span>
                <div className="space-y-2">
                  {selectedNode.callers?.map((c, i) => (
                    <div key={i} className="flex justify-between border-b border-slate-50 pb-1">
                      <span className="font-bold text-slate-700">{c.suspectName}</span>
                      <span className="text-slate-500 font-mono">{c.callCount} calls</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tower Specific Content */}
          {selectedNode.nodeType === "tower" && (
            <div className="flex flex-col gap-3 text-xs">
              <div className="space-y-1 font-mono text-slate-600 bg-slate-50 p-2 rounded">
                <div>Coords: {selectedNode.towerLat?.toFixed(4)}°N, {selectedNode.towerLon?.toFixed(4)}°E</div>
                <div>ID: {selectedNode.id}</div>
              </div>

              <div className="border-t border-slate-100 pt-3">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2 block">Visited By</span>
                <div className="space-y-2">
                  {selectedNode.connectedSuspects?.map((cs, i) => (
                    <div key={i} className="flex justify-between border-b border-slate-50 pb-1">
                      <span className="font-bold text-slate-700">{cs.suspectName}</span>
                      <span className="text-slate-500 font-mono">{cs.callCount} visits</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={rawEdges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
        proOptions={{ hideAttribution: true }}
        style={{ overflow: "visible" }}
      >
        <Background color="#cbd5e1" gap={16} size={1} />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default function NetworkGraph(props: Props) {
  return (
    <ReactFlowProvider>
      <NetworkGraphInner {...props} />
    </ReactFlowProvider>
  );
}
