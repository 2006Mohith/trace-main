import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import type { SuspectProfileOut } from "../lib/types";
import CallCalendar from "../components/CallCalendar";
import MovementMap from "../components/MovementMap";
import { Download, AlertTriangle, CheckCircle } from "lucide-react";
import { generatePdfReport } from "../lib/generatePdfReport";

function SeverityBadge({ sev }: { sev: string }) {
  if (sev === "HIGH") return <span className="badge-high">{sev}</span>;
  if (sev === "MEDIUM") return <span className="badge-medium">{sev}</span>;
  return <span className="badge-low">{sev}</span>;
}

function MetricBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] text-zinc-400 uppercase tracking-wide">{label}</span>
      <span className="text-[15px] font-semibold text-zinc-900">{value}</span>
    </div>
  );
}

function formatDate(s: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function eventSummary(ev: { event_type: string; detail: Record<string, unknown> }): string {
  const d = ev.detail;
  if (ev.event_type === "IMEI_SWAP") return `IMEI changed: ${d.old_imei} → ${d.new_imei}`;
  if (ev.event_type === "CO_LOCATION") return `Tower ${d.tower_id}`;
  if (ev.event_type === "COMMON_CONTACT") return `Shared: ${d.common_number}`;
  if (ev.event_type === "ANOMALY") return `Score: ${Number(d.anomaly_score).toFixed(3)}`;
  if (ev.event_type === "OTT_USAGE") return `${d.app}`;
  if (ev.event_type === "MULTI_SIM_IMEI") return `Burner Handset (IMEI: ${d.imei}) used with ${d.sim_count} SIMs`;
  if (ev.event_type === "CROSS_CASE_HANDLER") return `Global linkage: contact ${d.handler_number} appears in ${d.case_count} cases`;
  if (ev.event_type === "TOWER_SILENCE") return `Radio-silent for ${d.gap_hours} hrs. Last seen tower: ${d.last_seen_tower}`;
  if (ev.event_type === "NIGHT_CALL_BURST") return `Nocturnal burst: ${d.call_count} calls on ${d.night_date}`;
  if (ev.event_type === "LOOP_CALL") return `Urgent loop coordination: ${d.call_count_in_window} calls in ${d.window_minutes} mins`;
  return "—";
}

export default function SuspectProfilePage() {
  const { suspectId } = useParams<{ suspectId: string }>();
  const [profile, setProfile] = useState<SuspectProfileOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!suspectId) return;
    setLoading(true);
    api.getSuspectProfile(suspectId)
      .then(setProfile)
      .catch(() => setError("Failed to load suspect profile."))
      .finally(() => setLoading(false));
  }, [suspectId]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        <div className="text-xs text-zinc-400">← Back to Case</div>
        <div className="flex items-center justify-between">
          <div>
            <div className="w-48 h-6 bg-slate-200 rounded animate-pulse" />
            <div className="w-32 h-3 bg-slate-100 rounded animate-pulse mt-2" />
          </div>
        </div>

        {/* Call Summary Skeleton */}
        <div className="card">
          <h2 className="text-sm font-semibold text-zinc-900 mb-4">Call Summary</h2>
          <div className="grid grid-cols-6 gap-4 divide-x divide-zinc-100">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className={`flex flex-col gap-2 ${i > 1 ? "pl-4" : ""}`}>
                <div className="w-24 h-3 bg-slate-100 rounded animate-pulse" />
                <div className="w-16 h-8 bg-slate-200 rounded animate-pulse" />
              </div>
            ))}
          </div>
        </div>

        {/* Heatmap Skeleton */}
        <div className="card">
          <h2 className="text-sm font-semibold text-zinc-900 mb-4">Call Activity Heatmap</h2>
          <div className="bg-slate-100 animate-pulse w-full h-[160px] rounded-lg" />
        </div>

        {/* Map Skeleton */}
        <div className="card">
          <h2 className="text-sm font-semibold text-zinc-900 mb-4">Tower Movement</h2>
          <div className="bg-slate-100 animate-pulse w-full h-[200px] rounded-lg" />
        </div>
      </div>
    );
  }

  if (error || !profile) return <div className="p-8 text-red-600">{error || "Not found."}</div>;

  const { suspect, cdr_summary, ipdr_summary, events, call_heatmap_data, movement_data } = profile;
  const anomalyScore = cdr_summary?.anomaly_score;

  const hasAnomaly = events.some((e) => e.event_type === "ANOMALY");
  const hasImeiSwap = events.some((e) => e.event_type === "IMEI_SWAP");
  const hasMultiSimImei = events.some((e) => e.event_type === "MULTI_SIM_IMEI");
  const hasCrossCaseHandler = events.some((e) => e.event_type === "CROSS_CASE_HANDLER");
  const hasTowerSilence = events.some((e) => e.event_type === "TOWER_SILENCE");
  const hasLoopCall = events.some((e) => e.event_type === "LOOP_CALL");
  const hasNightCallBurst = events.some((e) => e.event_type === "NIGHT_CALL_BURST");

  const hasAnyRisk = hasAnomaly || hasImeiSwap || hasMultiSimImei || hasCrossCaseHandler || hasTowerSilence || hasLoopCall || hasNightCallBurst;

  const handleDownloadReport = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!suspectId) return;
    // In demo/mock mode (no backend), generate the full court-grade PDF client-side.
    // When a live backend is available, fall through to the server-generated PDF.
    const url = api.getReportUrl(suspectId);
    if (url.startsWith("data:")) {
      // Demo mode — generate real PDF using jsPDF
      try {
        // Derive case name from the case_id in the suspect object if possible
        const caseName = suspect.case_id ?? "Unknown Case";
        generatePdfReport(profile, caseName);
      } catch (err) {
        console.error("Failed to generate PDF report:", err);
      }
    } else {
      // Live backend — stream the server-generated PDF
      window.location.href = url;
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
      {/* Back link */}
      <Link
        to={`/cases/${suspect.case_id}`}
        className="text-xs text-zinc-400 hover:text-zinc-600 transition-colors"
      >
        ← Back to Case
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">{suspect.label}</h1>
          <span className="text-sm font-mono text-zinc-500">{suspect.primary_msisdn}</span>
        </div>
        <div className="flex items-center gap-3">
          {anomalyScore !== null && anomalyScore !== undefined && (
            <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${hasAnomaly ? "bg-red-100 text-red-700" : "bg-zinc-100 text-zinc-600"}`}>
              Anomaly {anomalyScore.toFixed(3)}
            </span>
          )}
          <button
            id="btn-download-report"
            onClick={handleDownloadReport}
            className="flex items-center gap-2 px-4 py-2 border border-zinc-200 rounded-lg text-sm text-zinc-700 hover:bg-zinc-50 transition-colors cursor-pointer"
          >
            <Download size={14} />
            Download Report
          </button>
        </div>
      </div>

      {/* Risk flags */}
      <div className="flex gap-3 flex-wrap">
        {hasImeiSwap && (
          <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs font-medium text-red-700">
            <AlertTriangle size={13} />
            IMEI Swap Detected
          </div>
        )}
        {hasMultiSimImei && (
          <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs font-medium text-red-700">
            <AlertTriangle size={13} />
            Burner IMEI / Multi-SIM Flagged
          </div>
        )}
        {hasCrossCaseHandler && (
          <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs font-medium text-red-700">
            <AlertTriangle size={13} />
            Cross-Case Handler Matched
          </div>
        )}
        {hasTowerSilence && (
          <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs font-medium text-amber-700">
            <AlertTriangle size={13} />
            Tower Switch-Off Detected
          </div>
        )}
        {hasLoopCall && (
          <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs font-medium text-red-700">
            <AlertTriangle size={13} />
            Loop Coordination Calls
          </div>
        )}
        {hasNightCallBurst && (
          <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs font-medium text-amber-700">
            <AlertTriangle size={13} />
            Nocturnal Burst Activity
          </div>
        )}
        {hasAnomaly && (
          <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs font-medium text-red-700">
            <AlertTriangle size={13} />
            Behavioural Anomaly Flagged
          </div>
        )}
        {!hasAnyRisk && (
          <div className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg text-xs font-medium text-green-700">
            <CheckCircle size={13} />
            No high-risk events detected
          </div>
        )}
      </div>

      {/* Section 1: Call Summary */}
      <div className="card">
        <h2 className="text-sm font-semibold text-zinc-900 mb-4">Call Summary</h2>
        {cdr_summary ? (
          <div className="grid grid-cols-6 gap-4 divide-x divide-[rgba(59,130,246,0.08)]">
            <MetricBox label="Total Calls" value={cdr_summary.total_calls} />
            <div className="pl-4"><MetricBox label="Total SMS" value={cdr_summary.total_sms} /></div>
            <div className="pl-4"><MetricBox label="Unique Contacts" value={cdr_summary.unique_contacts} /></div>
            <div className="pl-4"><MetricBox label="Avg Duration" value={`${cdr_summary.avg_duration_sec}s`} /></div>
            <div className="pl-4">
              <MetricBox
                label="Night Call Ratio"
                value={`${(cdr_summary.night_call_ratio * 100).toFixed(1)}%`}
              />
            </div>
            <div className="pl-4">
              <MetricBox label="Burst Score" value={cdr_summary.burst_score.toFixed(2)} />
            </div>
          </div>
        ) : (
          <p className="text-sm text-zinc-400">No CDR data available.</p>
        )}
      </div>

      {/* Section 2: Call Heatmap */}
      <div className="card">
        <h2 className="text-sm font-semibold text-zinc-900 mb-4">Call Activity Heatmap</h2>
        {call_heatmap_data.length > 0 ? (
          <CallCalendar data={call_heatmap_data} />
        ) : (
          <p className="text-sm text-zinc-400">No call data to display.</p>
        )}
      </div>

      {/* Section 3: Movement Timeline */}
      <div className="card">
        <h2 className="text-sm font-semibold text-zinc-900 mb-4">Tower Movement</h2>
        {movement_data.length > 0 ? (
          <>
            <div style={{ height: "380px" }} className="mb-4 rounded-lg overflow-hidden border border-zinc-100">
              <MovementMap movements={movement_data} events={events} suspectLabel={suspect.label} />
            </div>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-zinc-400 border-b border-[rgba(59,130,246,0.08)]">
                  <th className="pb-2 font-medium">Tower ID</th>
                  <th className="pb-2 font-medium">Timestamp</th>
                  <th className="pb-2 font-medium">Co-location With</th>
                </tr>
              </thead>
              <tbody>
                {movement_data.map((m, i) => (
                  <tr key={i} className="table-row-divider">
                    <td className={`py-2 font-mono pr-4 ${m.co_location ? "text-red-700 font-semibold" : "text-zinc-700"}`}>
                      {m.tower_id}
                    </td>
                    <td className="py-2 text-zinc-500 pr-4">{formatDate(m.timestamp)}</td>
                    <td className="py-2 text-zinc-600">
                      {m.co_location ? m.co_location_with.join(", ") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <p className="text-sm text-zinc-400">No tower data with coordinates available.</p>
        )}
      </div>

      {/* Section 4: Events */}
      <div className="card">
        <h2 className="text-sm font-semibold text-zinc-900 mb-4">Intelligence Events</h2>
        {events.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-zinc-400 border-b border-[rgba(59,130,246,0.08)]">
                <th className="pb-2 font-medium w-20">Severity</th>
                <th className="pb-2 font-medium w-32">Type</th>
                <th className="pb-2 font-medium">Summary</th>
                <th className="pb-2 font-medium w-36 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.id} className="table-row-divider">
                  <td className="py-2.5 pr-3"><SeverityBadge sev={ev.severity} /></td>
                  <td className="py-2.5 pr-3 text-zinc-600 font-mono text-xs">{ev.event_type}</td>
                  <td className="py-2.5 pr-3 text-zinc-700 text-xs">{eventSummary(ev)}</td>
                  <td className="py-2.5 text-zinc-400 text-xs text-right">{formatDate(ev.occurred_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-zinc-400">No events for this suspect. Run analysis on the case first.</p>
        )}

        {/* OTT Usage table */}
        {ipdr_summary && ipdr_summary.ott_breakdown.length > 0 && (
          <div className="mt-6 border-t border-[rgba(59,130,246,0.08)] pt-6">
            <h3 className="text-xs font-semibold text-zinc-700 mb-3 uppercase tracking-wide">OTT Application Usage</h3>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-zinc-400 border-b border-[rgba(59,130,246,0.08)]">
                  <th className="pb-2 font-medium">App</th>
                  <th className="pb-2 font-medium">Sessions</th>
                  <th className="pb-2 font-medium">Total Data</th>
                  <th className="pb-2 font-medium">First Seen</th>
                  <th className="pb-2 font-medium">Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {ipdr_summary.ott_breakdown.map((row, i) => (
                  <tr key={i} className="table-row-divider">
                    <td className="py-2 text-zinc-900 font-medium pr-4">{row.app}</td>
                    <td className="py-2 text-zinc-600 pr-4">{row.session_count}</td>
                    <td className="py-2 text-zinc-600 pr-4">{row.total_data_kb.toFixed(1)} KB</td>
                    <td className="py-2 text-zinc-500 pr-4">{row.first_seen ? new Date(row.first_seen).toLocaleDateString() : "—"}</td>
                    <td className="py-2 text-zinc-500">{row.last_seen ? new Date(row.last_seen).toLocaleDateString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>    </div>
  );
}
