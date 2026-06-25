import type { EventOut } from "../lib/types";

interface Props {
  events: EventOut[];
}

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
  if (ev.event_type === "IMEI_SWAP") return `IMEI: ${d.old_imei} → ${d.new_imei}`;
  if (ev.event_type === "CO_LOCATION") return `Tower ${d.tower_id}`;
  if (ev.event_type === "COMMON_CONTACT") return `${d.common_number}`;
  if (ev.event_type === "ANOMALY") return `Score ${Number(d.anomaly_score).toFixed(3)}`;
  if (ev.event_type === "OTT_USAGE") return `${d.app}`;
  return "—";
}

export default function EventTimeline({ events }: Props) {
  if (events.length === 0) {
    return <p className="text-sm text-zinc-400 py-4">No events to display.</p>;
  }
  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-2 top-2 bottom-2 w-px bg-zinc-100" />
      <div className="space-y-3 pl-8">
        {events.map((ev) => (
          <div key={ev.id} className="relative">
            {/* Dot */}
            <div
              className={`absolute -left-6 top-1.5 w-2 h-2 rounded-full border-2 border-white ${
                ev.severity === "HIGH" ? "bg-red-500" : ev.severity === "MEDIUM" ? "bg-amber-500" : "bg-zinc-400"
              }`}
            />
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <SeverityBadge sev={ev.severity} />
                  <span className="text-xs font-mono text-zinc-600">{ev.event_type}</span>
                </div>
                <p className="text-xs text-zinc-700">{eventSummary(ev)}</p>
                <p className="text-[10px] text-zinc-400 mt-0.5">{ev.involved_suspects.join(", ")}</p>
              </div>
              <span className="text-[10px] text-zinc-400 shrink-0">{formatDate(ev.occurred_at)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
