import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../lib/api";
import type { CaseOut, EventOut, SuspectOut } from "../lib/types";
import SuspectCard from "../components/SuspectCard";
import NetworkGraph from "../components/NetworkGraph";
import { Upload, Play, Loader2, AlertTriangle, Users, Activity, Phone } from "lucide-react";

type TabType = "network" | "events" | "suspects";

function SeverityBadge({ sev }: { sev: string }) {
  if (sev === "HIGH") return <span className="badge-high">{sev}</span>;
  if (sev === "MEDIUM") return <span className="badge-medium">{sev}</span>;
  return <span className="badge-low">{sev}</span>;
}

function formatDate(s: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function eventSummary(ev: EventOut): string {
  const d = ev.detail;
  if (ev.event_type === "IMEI_SWAP") return `IMEI changed: ${d.old_imei} → ${d.new_imei}`;
  if (ev.event_type === "CO_LOCATION") return `Tower ${d.tower_id} — ${(d.suspects_present as string[]).join(", ")}`;
  if (ev.event_type === "COMMON_CONTACT") return `Shared number: ${d.common_number}`;
  if (ev.event_type === "ANOMALY") return `Score ${Number(d.anomaly_score).toFixed(3)} — ${(d.triggered_features as string[]).join(", ")}`;
  if (ev.event_type === "OTT_USAGE") return `${d.app} — ${d.session_count} sessions, ${Number(d.total_data_kb).toFixed(0)} KB`;
  return JSON.stringify(d).slice(0, 80);
}

export default function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  const [caseData, setCaseData] = useState<CaseOut | null>(null);
  const [suspects, setSuspects] = useState<SuspectOut[]>([]);
  const [events, setEvents] = useState<EventOut[]>([]);
  const [sharedContacts, setSharedContacts] = useState<import("../lib/types").SharedContact[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeMsg, setAnalyzeMsg] = useState("");
  const [tab, setTab] = useState<TabType>("network");
  const [filterType, setFilterType] = useState("");
  const [filterSev, setFilterSev] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    if (!caseId) return;
    setLoading(true);
    try {
      const [c, s, e, sc] = await Promise.all([
        api.getCase(caseId),
        api.getSuspects(caseId),
        api.getEvents(caseId),
        api.getSharedContacts(caseId).catch(() => []),
      ]);
      setCaseData(c);
      setSuspects(s);
      setEvents(e);
      setSharedContacts(sc);
    } catch {
      setError("Failed to load case data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [caseId]);

  const handleAnalyze = async () => {
    if (!caseId) return;
    setAnalyzing(true);
    setAnalyzeMsg("");
    try {
      const res = await api.runAnalysis(caseId);
      setAnalyzeMsg(`Analysis complete. ${res.events_generated} events generated.`);
      load();
    } catch (err: unknown) {
      setAnalyzeMsg(`Error: ${String(err)}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const filteredEvents = events.filter((ev) => {
    if (filterType && ev.event_type !== filterType) return false;
    if (filterSev && ev.severity !== filterSev) return false;
    return true;
  });

  const highCount = events.filter((e) => e.severity === "HIGH").length;
  const commonContacts = new Set(
    events.filter((e) => e.event_type === "COMMON_CONTACT").map((e) => e.detail.common_number as string)
  ).size;

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-start justify-between mb-6">
          <div>
            <Link to="/" className="text-xs text-zinc-400 hover:text-zinc-600 transition-colors mb-2 block">← All Cases</Link>
            <div className="w-48 h-6 bg-slate-200 rounded animate-pulse" />
            <div className="w-32 h-3 bg-slate-100 rounded animate-pulse mt-2" />
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card border-l-2 border-l-blue-600">
              <div className="w-24 h-3 bg-slate-100 rounded animate-pulse mb-2" />
              <div className="w-16 h-8 bg-slate-200 rounded animate-pulse" />
            </div>
          ))}
        </div>
        <div className="border-b border-zinc-200 mb-6 pb-2">
          <div className="flex gap-4">
            <div className="w-16 h-4 bg-slate-200 rounded animate-pulse" />
            <div className="w-16 h-4 bg-slate-200 rounded animate-pulse" />
            <div className="w-16 h-4 bg-slate-200 rounded animate-pulse" />
          </div>
        </div>
        <div className="bg-slate-100 animate-pulse w-full h-[400px] rounded-lg" />
      </div>
    );
  }

  if (!caseData) return <div className="p-8 text-red-600">{error || "Case not found."}</div>;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link to="/" className="text-xs text-zinc-400 hover:text-zinc-600 transition-colors mb-2 block">← All Cases</Link>
          <h1 className="text-xl font-semibold text-zinc-900">{caseData.name}</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Created {new Date(caseData.created_at).toLocaleDateString("en-IN")} · ID: {caseId?.slice(0, 8)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            id="btn-upload-records"
            onClick={() => navigate(`/cases/${caseId}/upload`)}
            className="flex items-center gap-2 px-4 py-2 border border-zinc-200 rounded-lg text-sm text-zinc-700 hover:bg-zinc-50 transition-colors"
          >
            <Upload size={14} />
            Upload Records
          </button>
          <button
            id="btn-run-analysis"
            onClick={handleAnalyze}
            disabled={analyzing || suspects.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white rounded-lg text-sm font-medium disabled:opacity-40 hover:bg-zinc-700 transition-colors ring-1 ring-blue-700 ring-offset-1"
          >
            {analyzing ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            {analyzing ? "Analyzing…" : "Run Analysis"}
          </button>
        </div>
      </div>

      {analyzeMsg && (
        <div className={`mb-4 p-3 rounded-lg text-sm border ${analyzeMsg.startsWith("Error") ? "bg-red-50 border-red-200 text-red-700" : "bg-zinc-50 border-zinc-200 text-zinc-700"}`}>
          {analyzeMsg}
        </div>
      )}

      {/* Metric cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Suspects", value: suspects.length, icon: Users },
          { label: "Total Events", value: events.length, icon: Activity },
          { label: "High Severity", value: highCount, icon: AlertTriangle, alert: highCount > 0 },
          { label: "Common Contacts", value: commonContacts, icon: Phone },
        ].map(({ label, value, icon: Icon, alert }) => (
          <div key={label} className="card border-l-2 border-l-blue-600">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-zinc-500">{label}</span>
              <Icon size={14} className={alert ? "text-red-500" : "text-zinc-400"} />
            </div>
            <span className={`text-2xl font-semibold ${alert && value > 0 ? "text-red-600 bg-red-50 px-2 py-0.5 rounded" : "text-zinc-900"}`}>
              {value}
            </span>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-zinc-200 mb-6">
        <div className="flex gap-0">
          {(["network", "events", "suspects"] as TabType[]).map((t) => (
            <button
              key={t}
              id={`tab-${t}`}
              onClick={() => setTab(t)}
              className={`px-5 py-3 text-sm font-medium capitalize border-b-2 transition-colors ${
                tab === t
                  ? "border-zinc-900 text-zinc-900"
                  : "border-transparent text-zinc-500 hover:text-zinc-700"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Network tab */}
      {tab === "network" && (
        <div className="card" style={{ height: "520px" }}>
          {caseId && <NetworkGraph caseId={caseId} suspects={suspects} />}
        </div>
      )}

      {/* Events tab */}
      {tab === "events" && (
        <div className="card">
          {/* Filters */}
          <div className="flex gap-3 mb-4">
            <select
              id="filter-event-type"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="border border-zinc-200 rounded-lg px-3 py-1.5 text-sm text-zinc-700 bg-white focus:outline-none focus:ring-1 focus:ring-zinc-900"
            >
              <option value="">All Types</option>
              {["IMEI_SWAP", "CO_LOCATION", "COMMON_CONTACT", "ANOMALY", "OTT_USAGE"].map((t) => (
                <option key={t} value={t}>{t.replace("_", " ")}</option>
              ))}
            </select>
            <select
              id="filter-severity"
              value={filterSev}
              onChange={(e) => setFilterSev(e.target.value)}
              className="border border-zinc-200 rounded-lg px-3 py-1.5 text-sm text-zinc-700 bg-white focus:outline-none focus:ring-1 focus:ring-zinc-900"
            >
              <option value="">All Severities</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>
            <span className="text-xs text-zinc-400 self-center ml-auto">{filteredEvents.length} events</span>
          </div>

          {filteredEvents.length === 0 ? (
            <div className="text-center py-12 text-zinc-400 text-sm">
              {events.length === 0 ? "No events yet. Run analysis to generate intelligence." : "No events match the current filters."}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-zinc-400 border-b border-zinc-100">
                  <th className="pb-2 font-medium w-24">Severity</th>
                  <th className="pb-2 font-medium w-36">Type</th>
                  <th className="pb-2 font-medium">Suspects</th>
                  <th className="pb-2 font-medium">Summary</th>
                  <th className="pb-2 font-medium w-36 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.map((ev) => (
                  <tr key={ev.id} className="table-row-divider">
                    <td className="py-2.5 pr-3"><SeverityBadge sev={ev.severity} /></td>
                    <td className="py-2.5 pr-3 text-zinc-700 font-mono text-xs">{ev.event_type}</td>
                    <td className="py-2.5 pr-3 text-zinc-600 text-xs">{ev.involved_suspects.join(", ")}</td>
                    <td className="py-2.5 pr-3 text-zinc-700 text-xs">{eventSummary(ev)}</td>
                    <td className="py-2.5 text-zinc-400 text-xs text-right">{formatDate(ev.occurred_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Suspects tab */}
      {tab === "suspects" && (
        <div>
          {suspects.length === 0 ? (
            <div className="card text-center py-12 text-zinc-400 text-sm">
              No suspects yet.{" "}
              <button onClick={() => navigate(`/cases/${caseId}/upload`)} className="text-zinc-900 underline">
                Upload records
              </button>{" "}
              to add suspects.
            </div>
          ) : (
            <>
              <div className="flex flex-wrap gap-4">
                {suspects.map((s) => (
                  <SuspectCard
                    key={s.id}
                    suspect={s}
                    events={events}
                    onDelete={(id) => {
                      setSuspects((prev) => prev.filter((item) => item.id !== id));
                      // Re-load case detail to update metrics/graph/events
                      load();
                    }}
                  />
                ))}
              </div>

              {sharedContacts.length > 0 && (
                <div className="mt-8 bg-white border border-zinc-200 rounded-lg p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-semibold text-zinc-900">⚠ Shared Handler Numbers ({sharedContacts.length})</span>
                  </div>
                  <p className="text-xs text-zinc-500 mb-4">
                    Numbers appearing in CDRs of multiple suspects — potential coordinators or handlers.
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left border-collapse">
                      <thead>
                        <tr className="text-xs text-zinc-400 border-b border-zinc-100 pb-2">
                          <th className="pb-2 font-medium">Number</th>
                          <th className="pb-2 font-medium">Appears In</th>
                          <th className="pb-2 font-medium">Total Calls</th>
                          <th className="pb-2 font-medium text-right">Risk Level</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sharedContacts.map((c, i) => (
                          <tr key={i} className="border-b border-zinc-50 hover:bg-zinc-50/50">
                            <td className="py-3">
                              <span className="font-mono bg-zinc-100 text-zinc-800 px-1.5 py-0.5 rounded text-xs">
                                {c.number}
                              </span>
                            </td>
                            <td className="py-3 text-zinc-600 text-xs">{c.suspects.join(', ')}</td>
                            <td className="py-3 text-zinc-600 text-xs">{c.total_calls} calls</td>
                            <td className="py-3 text-right">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                                c.suspect_count >= 3
                                  ? 'bg-red-50 text-red-700 ring-1 ring-red-600/10'
                                  : 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/10'
                              }`}>
                                {c.suspect_count >= 3 ? 'HIGH' : 'MEDIUM'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
