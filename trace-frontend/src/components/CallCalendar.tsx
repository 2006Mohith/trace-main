import type { CallHeatmapRow } from "../lib/types";

interface Props {
  data: CallHeatmapRow[];
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

function getColor(count: number, max: number): string {
  if (count === 0 || max === 0) return "#ffffff";
  const ratio = count / max;
  if (ratio < 0.25) return "#d4d4d8"; // zinc-300
  if (ratio < 0.5) return "#71717a";  // zinc-500
  if (ratio < 0.75) return "#3f3f46"; // zinc-700
  return "#18181b";                    // zinc-900
}

export default function CallCalendar({ data }: Props) {
  // Build lookup map
  const countMap: Record<string, number> = {};
  let maxCount = 0;
  for (const row of data) {
    const key = `${row.day_of_week}-${row.hour_of_day}`;
    countMap[key] = (countMap[key] || 0) + row.call_count;
    if (countMap[key] > maxCount) maxCount = countMap[key];
  }

  return (
    <div>
      {/* Hour labels */}
      <div className="flex ml-10 mb-1">
        {HOURS.map((h) => (
          <div
            key={h}
            style={{ width: 14, marginRight: 2, fontSize: 8, textAlign: "center" }}
            className="text-zinc-400"
          >
            {h % 3 === 0 ? h : ""}
          </div>
        ))}
      </div>

      {/* Grid */}
      {DAYS.map((day, dayIdx) => (
        <div key={day} className="flex items-center mb-0.5">
          <span className="text-[10px] text-zinc-400 w-8 text-right pr-2 shrink-0">{day}</span>
          {HOURS.map((hour) => {
            const key = `${dayIdx}-${hour}`;
            const count = countMap[key] || 0;
            const color = getColor(count, maxCount);
            return (
              <div
                key={hour}
                title={`${day} ${hour}:00 — ${count} call${count !== 1 ? "s" : ""}`}
                style={{
                  width: 14,
                  height: 14,
                  marginRight: 2,
                  borderRadius: 2,
                  backgroundColor: color,
                  cursor: count > 0 ? "pointer" : "default",
                }}
              />
            );
          })}
        </div>
      ))}

      {/* Legend */}
      <div className="flex items-center gap-2 mt-3 ml-10">
        <span className="text-[10px] text-zinc-400">Less</span>
        {["#ffffff", "#d4d4d8", "#71717a", "#3f3f46", "#18181b"].map((c) => (
          <div key={c} style={{ width: 12, height: 12, backgroundColor: c, borderRadius: 2, border: "1px solid #e4e4e7" }} />
        ))}
        <span className="text-[10px] text-zinc-400">More</span>
      </div>
    </div>
  );
}
