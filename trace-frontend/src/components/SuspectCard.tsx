import { useNavigate } from "react-router-dom";
import type { SuspectOut, EventOut } from "../lib/types";
import { Trash2 } from "lucide-react";
import { api } from "../lib/api";

interface Props {
  suspect: SuspectOut;
  events: EventOut[];
  onDelete?: (id: string) => void;
}

export default function SuspectCard({ suspect, events, onDelete }: Props) {
  const navigate = useNavigate();

  const suspectEvents = events.filter((e) => e.involved_suspects.includes(suspect.label));
  const imeiCount = suspectEvents.filter((e) => e.event_type === "IMEI_SWAP").length;
  const coLocCount = suspectEvents.filter((e) => e.event_type === "CO_LOCATION").length;
  const anomalyEvent = suspectEvents.find((e) => e.event_type === "ANOMALY");
  const anomalyScore = anomalyEvent?.detail?.anomaly_score as number | undefined;

  // Normalize anomaly score for bar display: score is negative (-1 to 0), more negative = worse
  const normalizedScore = anomalyScore != null ? Math.min(1, Math.abs(anomalyScore) * 2) : 0;

  return (
    <div
      id={`suspect-card-${suspect.id}`}
      onClick={() => navigate(`/suspects/${suspect.id}`)}
      className="card text-left hover:border-zinc-400 hover:shadow-sm transition-all cursor-pointer group relative flex flex-col justify-between"
      style={{ width: 200 }}
    >
      <div>
        <div className="flex items-start justify-between mb-0.5">
          <p className="text-sm font-bold text-zinc-900 group-hover:text-zinc-700 transition-colors">
            {suspect.label}
          </p>
          <button
            onClick={async (e) => {
              e.stopPropagation();
              if (window.confirm(`Are you sure you want to delete suspect "${suspect.label}"? All associated CDR/IPDR rows will be permanently deleted.`)) {
                try {
                  await api.deleteSuspect(suspect.id);
                  if (onDelete) onDelete(suspect.id);
                } catch (err: unknown) {
                  alert("Failed to delete suspect: " + String(err));
                }
              }
            }}
            className="p-1 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Delete Suspect"
          >
            <Trash2 size={12} />
          </button>
        </div>
        <p className="text-[11px] font-mono text-zinc-500 mb-4 break-all">{suspect.primary_msisdn}</p>
      </div>

      {/* Anomaly score bar */}
      <div className="mb-3">
        <div className="flex justify-between text-[10px] text-zinc-400 mb-1">
          <span>Anomaly Score</span>
          <span>{anomalyScore != null ? anomalyScore.toFixed(3) : "—"}</span>
        </div>
        <div className="h-1.5 bg-zinc-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${normalizedScore * 100}%`,
              backgroundColor: normalizedScore > 0.5 ? "#f87171" : "#a1a1aa",
            }}
          />
        </div>
      </div>

      {/* Event badges */}
      <div className="flex flex-wrap gap-1">
        {imeiCount > 0 && (
          <span className="badge-high" title="IMEI Swap events">
            IMEI ×{imeiCount}
          </span>
        )}
        {coLocCount > 0 && (
          <span className="badge-medium" title="Co-location events">
            CO-LOC ×{coLocCount}
          </span>
        )}
        {anomalyEvent && (
          <span className="badge-high" title="Anomaly detected">
            ANOMALY
          </span>
        )}
        {suspectEvents.length === 0 && (
          <span className="badge-low">CLEAN</span>
        )}
      </div>
    </div>
  );
}
