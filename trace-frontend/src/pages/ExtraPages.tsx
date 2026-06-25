import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import type { CaseOut, SuspectOut } from "../lib/types";
import {
  Search,
  Download,
  Loader2,
  Server,
  CheckCircle,
  XCircle,
  RefreshCw,
  User,
  Activity,
  Bell,
  FileBarChart,
  Lock,
  MapPin,
  Shield,
  Radio,
  Target,
} from "lucide-react";

export function DashboardPage() {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalCases: 0,
    totalSuspects: 0,
    totalEvents: 0,
    highSeverityEvents: 0,
  });

  useEffect(() => {
    setLoading(true);
    api.getCases()
      .then(async (allCases) => {
        setCases(allCases);
        let suspects = 0;
        let events = 0;
        allCases.forEach((c) => {
          suspects += c.suspect_count || 0;
          events += c.event_count || 0;
        });

        let highCount = 0;
        for (const c of allCases) {
          try {
            const highEvents = await api.getEvents(c.id, undefined, "HIGH");
            highCount += highEvents.length;
          } catch (e) {
            console.error(e);
          }
        }

        setStats({
          totalCases: allCases.length,
          totalSuspects: suspects,
          totalEvents: events,
          highSeverityEvents: highCount,
        });
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 animate-pulse bg-white/60 rounded-md border border-zinc-200" />
          ))}
        </div>
        <div className="h-64 animate-pulse bg-white/60 rounded-md border border-zinc-200" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">

      {/* ══ HERO SECTION ══ Emblem prominent center, title beside */}
      <div className="bg-white/75 backdrop-blur-sm border border-zinc-200/80 rounded-md overflow-hidden">
        {/* Top accent strip */}
        <div className="h-[3px] w-full bg-zinc-900" />
        <div className="flex items-center gap-0">
          {/* Left: Large Emblem block */}
          <div className="flex items-center justify-center shrink-0 px-6 py-5 border-r border-zinc-200/60 bg-zinc-50/50" style={{ width: "160px" }}>
            <div className="w-[110px] h-[110px] pointer-events-none select-none flex items-center justify-center">
              <img
                src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg"
                alt="Emblem of India"
                className="w-full h-full object-contain"
              />
            </div>
          </div>
                    {/* Middle: Title + subtitle */}
          <div className="flex-1 px-7 py-6 flex items-center justify-between gap-4">
            <div>
              <div className="text-[9px] font-mono tracking-[0.25em] text-zinc-500 font-bold uppercase mb-1.5">
                Prakasham District Police · Criminal Intelligence Division
              </div>
              <h1 className="text-[17px] font-bold tracking-wide text-zinc-900 font-sans uppercase leading-tight">
                Telecom Record Analysis for Criminal Examination
              </h1>
              <p className="text-[10px] text-zinc-400 font-mono mt-1 uppercase">
                Jurisdiction Corridor: Ongole · Chirala · Markapur · Kandukur (AP)
              </p>
            </div>
            <img
              src="/prakasham-police.png"
              alt="Prakasham District Police Seal"
              className="h-14 w-14 object-contain opacity-90 hidden md:block shrink-0"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          </div>

          {/* Right: Status badge */}
          <div className="shrink-0 px-7 py-6 flex flex-col items-end gap-2 border-l border-zinc-200/60">
            <span className="inline-block text-[8px] font-mono uppercase tracking-widest text-red-600 border border-red-300 bg-red-50 px-2.5 py-1 rounded-sm">
              CLASSIFIED
            </span>
            <span className="text-[9px] text-zinc-400 font-mono uppercase tracking-wide">
              Sec 70B IT Act
            </span>
          </div>
        </div>
      </div>

      {/* ══ STATS ROW ══ Semi-transparent so emblem shows through */}
      <div className="grid grid-cols-4 gap-4">
        {/* Total Cases */}
        <div className="bg-white/70 backdrop-blur-sm border border-zinc-200/80 border-t-[3px] border-t-zinc-800 p-5 rounded-md flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase tracking-widest font-mono">Total Cases</span>
          <p className="text-4xl font-bold text-zinc-950 mt-2 font-mono">{String(stats.totalCases).padStart(2, '0')}</p>
          <span className="text-[8px] text-zinc-400 font-mono mt-2 uppercase">Database online</span>
        </div>

        {/* Suspects */}
        <div className="bg-white/70 backdrop-blur-sm border border-zinc-200/80 border-t-[3px] border-t-zinc-800 p-5 rounded-md flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase tracking-widest font-mono">Suspects</span>
          <p className="text-4xl font-bold text-zinc-950 mt-2 font-mono">{String(stats.totalSuspects).padStart(2, '0')}</p>
          <span className="text-[8px] text-zinc-400 font-mono mt-2 uppercase">Active tracking</span>
        </div>

        {/* CDR Events */}
        <div className="bg-white/70 backdrop-blur-sm border border-zinc-200/80 border-t-[3px] border-t-zinc-800 p-5 rounded-md flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase tracking-widest font-mono">CDR Events</span>
          <p className="text-4xl font-bold text-zinc-950 mt-2 font-mono">{stats.totalEvents}</p>
          <span className="text-[8px] text-zinc-400 font-mono mt-2 uppercase">Audit logged</span>
        </div>

        {/* High Alerts */}
        <div className="bg-white/70 backdrop-blur-sm border border-zinc-200/80 border-t-[3px] border-t-red-600 p-5 rounded-md flex flex-col justify-between">
          <span className="text-[9px] text-zinc-400 uppercase tracking-widest font-mono">High Alerts</span>
          <p className={`text-4xl font-bold mt-2 font-mono ${stats.highSeverityEvents > 0 ? "text-red-700" : "text-zinc-950"}`}>
            {String(stats.highSeverityEvents).padStart(2, '0')}
          </p>
          <span className={`text-[8px] font-mono mt-2 uppercase ${stats.highSeverityEvents > 0 ? "text-red-500" : "text-zinc-400"}`}>
            {stats.highSeverityEvents > 0 ? "⚠ Action required" : "Clear"}
          </span>
        </div>
      </div>

      {/* ══ MAIN CONTENT GRID ══ */}
      <div className="grid grid-cols-3 gap-5">

        {/* Left 2/3: Recent Active Investigations */}
        <div className="col-span-2">
          <div className="bg-white/75 backdrop-blur-sm border border-zinc-200/80 rounded-md overflow-hidden">
            <div className="px-5 py-4 border-b border-zinc-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-900 font-sans uppercase tracking-wider">
                Recent Active Investigations
              </h2>
              <Link
                to="/cases"
                className="text-[10px] font-mono text-zinc-500 hover:text-zinc-800 uppercase tracking-widest border border-zinc-200 px-2 py-0.5 rounded-sm hover:bg-zinc-50 transition-colors"
              >
                All Cases →
              </Link>
            </div>
            <div className="divide-y divide-zinc-100/80">
              {cases.slice(0, 5).map((c) => (
                <div key={c.id} className="px-5 py-3.5 flex items-center justify-between hover:bg-zinc-50/60 transition-colors">
                  <div>
                    <Link
                      to={`/cases/${c.id}`}
                      className="text-sm font-semibold text-zinc-900 hover:text-blue-700 transition-colors font-sans"
                    >
                      {c.name}
                    </Link>
                    <p className="text-[10px] text-zinc-400 mt-0.5 font-mono">
                      ID: {c.id.slice(0, 8)} &nbsp;·&nbsp; {new Date(c.created_at).toLocaleDateString("en-IN")}
                    </p>
                  </div>
                  <div className="flex gap-5 text-xs font-mono">
                    <span className="text-zinc-500">{c.suspect_count} suspect(s)</span>
                    <span className={c.event_count > 0 ? "text-red-600 font-bold" : "text-zinc-400"}>
                      {c.event_count} event(s)
                    </span>
                  </div>
                </div>
              ))}
              {cases.length === 0 && (
                <p className="text-xs text-zinc-400 py-8 text-center font-mono">No active cases in database.</p>
              )}
            </div>
          </div>
        </div>

        {/* Right 1/3: System Node Status */}
        <div className="col-span-1 space-y-4">
          {/* Core Node Status */}
          <div className="bg-white/75 backdrop-blur-sm border border-zinc-200/80 rounded-md overflow-hidden">
            <div className="px-5 py-4 border-b border-zinc-100">
              <h2 className="text-sm font-semibold text-zinc-900 font-sans uppercase tracking-wider">System Status</h2>
            </div>
            <div className="px-5 py-4 space-y-3.5 text-xs font-sans">
              <div className="flex items-center justify-between">
                <span className="text-zinc-500">Database Engine</span>
                <span className="px-2 py-0.5 bg-green-50 text-green-700 font-mono text-[10px] rounded border border-green-200">ONLINE</span>
              </div>
              <div className="flex items-center justify-between border-t border-zinc-50 pt-3">
                <span className="text-zinc-500">FastAPI Service</span>
                <span className="px-2 py-0.5 bg-green-50 text-green-700 font-mono text-[10px] rounded border border-green-200">ONLINE</span>
              </div>
              <div className="flex items-center justify-between border-t border-zinc-50 pt-3">
                <span className="text-zinc-500">Server Uptime</span>
                <span className="text-zinc-700 font-mono">99.98%</span>
              </div>
              <div className="flex items-center justify-between border-t border-zinc-50 pt-3">
                <span className="text-zinc-500">Security Mode</span>
                <span className="text-red-600 font-bold tracking-wider font-mono text-[10px]">RESTRICTED</span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white/75 backdrop-blur-sm border border-zinc-200/80 rounded-md overflow-hidden">
            <div className="px-5 py-4 border-b border-zinc-100">
              <h2 className="text-sm font-semibold text-zinc-900 font-sans uppercase tracking-wider">Quick Actions</h2>
            </div>
            <div className="px-5 py-4 space-y-2">
              <Link
                to="/cases"
                className="block w-full text-left px-3 py-2.5 bg-zinc-900 text-white text-xs font-mono uppercase tracking-wider rounded-sm hover:bg-zinc-800 transition-colors text-center"
              >
                + New Case
              </Link>
              <Link
                to="/suspects"
                className="block w-full text-left px-3 py-2.5 border border-zinc-200 text-zinc-700 text-xs font-mono uppercase tracking-wider rounded-sm hover:bg-zinc-50 transition-colors text-center"
              >
                Suspect Registry
              </Link>
              <Link
                to="/reports"
                className="block w-full text-left px-3 py-2.5 border border-zinc-200 text-zinc-700 text-xs font-mono uppercase tracking-wider rounded-sm hover:bg-zinc-50 transition-colors text-center"
              >
                Download Reports
              </Link>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

interface SuspectExtended extends SuspectOut {
  caseName: string;
  eventCount: number;
}

export function SuspectsPage() {
  const [suspects, setSuspects] = useState<SuspectExtended[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    api.getCases()
      .then(async (allCases) => {
        const list: SuspectExtended[] = [];
        for (const c of allCases) {
          try {
            const suspectsInCase = await api.getSuspects(c.id);
            suspectsInCase.forEach((s) => {
              list.push({
                ...s,
                caseName: c.name,
                eventCount: c.event_count, // rough estimate or filter later
              });
            });
          } catch (err) {
            console.error(err);
          }
        }
        setSuspects(list);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const filteredSuspects = suspects.filter(
    (s) =>
      s.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.primary_msisdn.includes(searchQuery)
  );

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 mb-1">Suspect Registry</h1>
          <div className="flex items-center gap-1.5 mt-1 text-[11px] text-slate-500 font-medium">
            <img
              src="/prakasham-police.png"
              alt=""
              className="h-4 object-contain opacity-75 animate-none"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
            <span>Prakasham District Police · Intelligence Database</span>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative w-64">
          <input
            type="text"
            placeholder="Search by label or phone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 border border-zinc-200 rounded-lg text-xs text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-zinc-900"
          />
          <Search size={14} className="absolute left-3 top-2.5 text-zinc-400" />
        </div>
      </div>

      <div className="card">
        {loading ? (
          <div className="py-12 flex justify-center items-center">
            <Loader2 className="animate-spin text-zinc-400" />
          </div>
        ) : filteredSuspects.length === 0 ? (
          <div className="py-12 text-center text-zinc-400 text-sm">
            No suspects found.
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-zinc-400 border-b border-[rgba(59,130,246,0.08)]">
                <th className="pb-3 font-medium">Suspect Label</th>
                <th className="pb-3 font-medium">Primary MSISDN</th>
                <th className="pb-3 font-medium">Associated Operation</th>
                <th className="pb-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {filteredSuspects.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 font-medium text-zinc-900">{s.label}</td>
                  <td className="py-3 font-mono text-zinc-600">{s.primary_msisdn}</td>
                  <td className="py-3 text-zinc-500">{s.caseName}</td>
                  <td className="py-3 text-right">
                    <button
                      onClick={() => navigate(`/suspects/${s.id}`)}
                      className="px-3 py-1 bg-zinc-900 text-white rounded text-[11px] hover:bg-zinc-800 transition-colors cursor-pointer"
                    >
                      View Profile
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export function ReportsPage() {
  const [suspects, setSuspects] = useState<SuspectExtended[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getCases()
      .then(async (allCases) => {
        const list: SuspectExtended[] = [];
        for (const c of allCases) {
          try {
            const suspectsInCase = await api.getSuspects(c.id);
            suspectsInCase.forEach((s) => {
              list.push({
                ...s,
                caseName: c.name,
                eventCount: c.event_count,
              });
            });
          } catch (err) {
            console.error(err);
          }
        }
        setSuspects(list);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 mb-1">Investigation Briefs</h1>
        <p className="text-xs text-zinc-500 uppercase tracking-widest font-mono">Download legal-ready investigative reports for court brief support</p>
      </div>

      <div className="card">
        {loading ? (
          <div className="py-12 flex justify-center items-center">
            <Loader2 className="animate-spin text-zinc-400" />
          </div>
        ) : suspects.length === 0 ? (
          <div className="py-12 text-center text-zinc-400 text-sm">
            No active reports available.
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-zinc-400 border-b border-[rgba(59,130,246,0.08)]">
                <th className="pb-3 font-medium">Suspect Profile</th>
                <th className="pb-3 font-medium">Phone No</th>
                <th className="pb-3 font-medium">Case Name</th>
                <th className="pb-3 font-medium text-right">Download Brief</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {suspects.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 font-semibold text-zinc-900">{s.label}</td>
                  <td className="py-3 font-mono text-zinc-500">{s.primary_msisdn}</td>
                  <td className="py-3 text-zinc-600">{s.caseName}</td>
                  <td className="py-3 text-right">
                    <Link
                      to={`/suspects/${s.id}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-zinc-200 rounded hover:bg-zinc-50 text-[11px] text-zinc-700 transition-colors cursor-pointer"
                    >
                      <Download size={12} />
                      Download via Profile
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export function SettingsPage() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [backendPing, setBackendPing] = useState<number | null>(null);
  const [alertThreshold, setAlertThreshold] = useState("10");
  const [maxCallGap, setMaxCallGap] = useState("6");
  const [towerRadius, setTowerRadius] = useState("2");
  const [retentionDays, setRetentionDays] = useState("90");
  const [exportFormat, setExportFormat] = useState("pdf");
  const [sessionName] = useState("Inspector Sharma");
  const [badgeNo] = useState("AP-TN-2847");
  const [unit] = useState("Prakasam District SP Office");

  const checkBackend = useCallback(async () => {
    setBackendStatus("checking");
    const t0 = Date.now();
    try {
      const res = await fetch("http://localhost:8000/health", { signal: AbortSignal.timeout(4000) });
      if (res.ok) {
        setBackendPing(Date.now() - t0);
        setBackendStatus("online");
      } else {
        setBackendStatus("offline");
      }
    } catch {
      setBackendStatus("offline");
    }
  }, []);

  useEffect(() => { checkBackend(); }, [checkBackend]);

  const now = new Date();
  const sessionDate = now.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  const sessionTime = now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

  const sectionHeader = (icon: React.ReactNode, title: string, subtitle: string) => (
    <div className="flex items-center gap-3 mb-5 pb-3 border-b border-zinc-100">
      <div className="text-zinc-500">{icon}</div>
      <div>
        <h2 className="text-sm font-semibold text-zinc-900">{title}</h2>
        <p className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider mt-0.5">{subtitle}</p>
      </div>
    </div>
  );

  const field = (label: string, value: string, mono = false) => (
    <div className="flex items-center justify-between py-2 border-b border-zinc-50 last:border-0">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className={`text-xs font-medium text-zinc-800 ${mono ? "font-mono" : ""}`}>{value}</span>
    </div>
  );

  const inputRow = (label: string, sublabel: string, value: string, setter: (v: string) => void, unit: string, type = "number") => (
    <div className="flex items-center justify-between gap-4">
      <div className="flex-1">
        <p className="text-xs font-medium text-zinc-800">{label}</p>
        <p className="text-[10px] text-zinc-400 mt-0.5">{sublabel}</p>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <input
          type={type}
          value={value}
          onChange={(e) => setter(e.target.value)}
          className="w-16 border border-zinc-200 rounded px-2 py-1 text-xs text-center focus:outline-none focus:ring-1 focus:ring-zinc-900 font-mono bg-white"
        />
        <span className="text-[10px] text-zinc-400 font-mono">{unit}</span>
      </div>
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-6 overflow-visible">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 mb-1">Investigation Settings</h1>
        <p className="text-xs text-zinc-500 uppercase tracking-widest font-mono">
          Configure TRACE analysis parameters, thresholds, and workstation preferences
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LEFT COLUMN */}
        <div className="space-y-6">

          {/* 1. Investigator Profile */}
          <div className="card">
            {sectionHeader(<User size={16} />, "Investigator Profile", "Active session credentials")}
            <div className="space-y-1">
              {field("Name / Rank", sessionName)}
              {field("Badge No.", badgeNo, true)}
              {field("Unit", unit)}
              {field("Session Started", `${sessionDate}, ${sessionTime}`)}
              {field("Auth Mode", "LOCAL_INSPECTOR_SESSION", true)}
            </div>
          </div>

          {/* 2. CDR Analysis Thresholds */}
          <div className="card">
            {sectionHeader(<Activity size={16} />, "CDR Analysis Thresholds", "Controls burst detection sensitivity")}
            <div className="space-y-4">
              {inputRow(
                "Burst Call Threshold",
                "Flag suspects exceeding N calls in a 1-hour window",
                alertThreshold, setAlertThreshold, "calls/hr"
              )}
              <div className="border-t border-zinc-50 pt-4" />
              {inputRow(
                "Max Call Gap (Dormancy)",
                "Mark CDR record as dormant if no calls within N hours",
                maxCallGap, setMaxCallGap, "hours"
              )}
            </div>
          </div>

          {/* 3. Alert Rules */}
          <div className="card">
            {sectionHeader(<Bell size={16} />, "Alert Rules", "Severity trigger configuration")}
            <div className="space-y-4">
              {inputRow(
                "Tower Coverage Radius",
                "Maximum radius for tower-to-device mapping in geospatial analysis",
                towerRadius, setTowerRadius, "km"
              )}
              <div className="border-t border-zinc-50 pt-4" />
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-zinc-800">Cross-District Alert</p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">Flag suspect if phone towers cross district boundaries</p>
                </div>
                <span className="text-[10px] font-mono text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded">ENABLED</span>
              </div>
              <div className="flex items-center justify-between border-t border-zinc-50 pt-3">
                <div>
                  <p className="text-xs font-medium text-zinc-800">SIM Swap Detection</p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">Alert when same IMEI appears with multiple SIMs</p>
                </div>
                <span className="text-[10px] font-mono text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded">ENABLED</span>
              </div>
              <div className="flex items-center justify-between border-t border-zinc-50 pt-3">
                <div>
                  <p className="text-xs font-medium text-zinc-800">Late-Night Call Pattern</p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">Flag 00:00–04:00 IST activity as HIGH severity</p>
                </div>
                <span className="text-[10px] font-mono text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">REVIEW</span>
              </div>
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN */}
        <div className="space-y-6">

          {/* 4. Backend / API Status */}
          <div className="card">
            {sectionHeader(<Server size={16} />, "Backend Node Status", "TRACE API connectivity")}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {backendStatus === "checking" && <Loader2 size={14} className="animate-spin text-zinc-400" />}
                  {backendStatus === "online" && <CheckCircle size={14} className="text-green-600" />}
                  {backendStatus === "offline" && <XCircle size={14} className="text-red-500" />}
                  <span className="text-xs font-medium text-zinc-800">
                    {backendStatus === "checking" ? "Checking..." : backendStatus === "online" ? "Backend Online" : "Backend Offline"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {backendPing !== null && backendStatus === "online" && (
                    <span className="text-[10px] font-mono text-zinc-400">{backendPing}ms</span>
                  )}
                  <button
                    onClick={checkBackend}
                    className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-900 border border-zinc-200 px-2 py-1 rounded transition-colors cursor-pointer"
                  >
                    <RefreshCw size={10} />
                    Retry
                  </button>
                </div>
              </div>

              {backendStatus === "offline" && (
                <div className="bg-red-50 border border-red-200 rounded p-3">
                  <p className="text-[10px] font-mono text-red-700 font-semibold mb-1">CONNECTION FAILED</p>
                  <p className="text-[10px] text-red-600">Cannot reach http://localhost:8000. Start the backend server:</p>
                  <code className="block mt-1.5 text-[10px] bg-red-100 text-red-800 p-1.5 rounded font-mono">
                    uvicorn main:app --reload
                  </code>
                </div>
              )}

              <div className="border-t border-zinc-50 pt-3 space-y-1">
                {field("Endpoint", "http://localhost:8000", true)}
                {field("TRACE Version", "v1.0.0", true)}
                {field("Database", "SQLite · trace.db", true)}
                {field("CORS Origin", "localhost:5173", true)}
              </div>
            </div>
          </div>

          {/* 5. Data & Export Settings */}
          <div className="card">
            {sectionHeader(<FileBarChart size={16} />, "Data & Export", "Report generation and retention")}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-zinc-800">Report Format</p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">Default format for investigation briefs</p>
                </div>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value)}
                  className="border border-zinc-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-zinc-900 bg-white font-mono"
                >
                  <option value="pdf">PDF</option>
                  <option value="csv">CSV</option>
                  <option value="json">JSON</option>
                </select>
              </div>
              <div className="border-t border-zinc-50 pt-3">
                {inputRow(
                  "CDR Retention Period",
                  "Automatically purge raw CDR records older than N days",
                  retentionDays, setRetentionDays, "days"
                )}
              </div>
            </div>
          </div>

          {/* 6. Audit & Security */}
          <div className="card">
            {sectionHeader(<Lock size={16} />, "Audit & Security", "Access logging and chain of custody")}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-zinc-800">Session Audit Logging</p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">Log all investigator actions for court admissibility</p>
                </div>
                <span className="text-[10px] font-mono text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded">ENABLED</span>
              </div>
              <div className="flex items-center justify-between border-t border-zinc-50 pt-3">
                <div>
                  <p className="text-xs font-medium text-zinc-800">IP Address Logging</p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">Record workstation IP on each login (Sec 70B IT Act)</p>
                </div>
                <span className="text-[10px] font-mono text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded">ENABLED</span>
              </div>
              <div className="flex items-center justify-between border-t border-zinc-50 pt-3">
                <div>
                  <p className="text-xs font-medium text-zinc-800">Chain of Custody Watermark</p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">Stamp investigator badge on all exported reports</p>
                </div>
                <span className="text-[10px] font-mono text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded">ENABLED</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

// GEO INTEL PAGE
export function GeoIntelPage() {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [centerLat, setCenterLat] = useState("15.5057");
  const [centerLon, setCenterLon] = useState("80.0499");
  const [radiusKm, setRadiusKm] = useState("5.0");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<{
    query: Record<string, any>;
    hits: {
      suspect_id: string;
      suspect_label: string;
      msisdn: string;
      tower_id: string;
      tower_lat: number;
      tower_lon: number;
      distance_km: number;
      timestamp: string;
      call_type: string;
      duration_sec: number | null;
    }[];
    suspects_found: string[];
    total_hits: number;
  } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getCases()
      .then((res) => {
        setCases(res);
        if (res.length > 0) {
          setSelectedCaseId(res[0].id);
        }
      })
      .catch((err) => {
        console.error("Failed to load cases", err);
        setError("Failed to load active cases list.");
      });
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCaseId) {
      setError("Please select a case first.");
      return;
    }
    setLoading(true);
    setError("");
    setResults(null);
    try {
      const lat = parseFloat(centerLat);
      const lon = parseFloat(centerLon);
      const rad = parseFloat(radiusKm);
      if (isNaN(lat) || isNaN(lon) || isNaN(rad)) {
        throw new Error("Latitude, Longitude and Radius must be valid numbers.");
      }
      const data = await api.radialSearch(
        selectedCaseId,
        lat,
        lon,
        rad,
        startTime || undefined,
        endTime || undefined
      );
      setResults(data);
    } catch (err: any) {
      setError(err.message || "Failed to execute radial search.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 flex items-center gap-2">
          <MapPin className="text-blue-500 w-5 h-5 animate-pulse" />
          Radial Search & Tower Buffer Zones
        </h1>
        <p className="text-xs text-zinc-500 mt-1">
          Query suspects whose cell tower pings occurred within a specific geographical radius of a crime scene or coordinates.
        </p>
      </div>

      <div className="card">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-[11px] text-zinc-500 uppercase tracking-wider font-semibold mb-1">
                Select Case
              </label>
              <select
                value={selectedCaseId}
                onChange={(e) => setSelectedCaseId(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-slate-400 font-sans"
              >
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
                {cases.length === 0 && <option value="">No cases available</option>}
              </select>
            </div>

            <div>
              <label className="block text-[11px] text-zinc-500 uppercase tracking-wider font-semibold mb-1">
                Crime Scene Latitude
              </label>
              <input
                type="text"
                value={centerLat}
                onChange={(e) => setCenterLat(e.target.value)}
                placeholder="e.g. 15.5057"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-slate-400 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] text-zinc-500 uppercase tracking-wider font-semibold mb-1">
                Crime Scene Longitude
              </label>
              <input
                type="text"
                value={centerLon}
                onChange={(e) => setCenterLon(e.target.value)}
                placeholder="e.g. 80.0499"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-slate-400 font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-[11px] text-zinc-500 uppercase tracking-wider font-semibold mb-1">
                Radius (Kilometres)
              </label>
              <input
                type="text"
                value={radiusKm}
                onChange={(e) => setRadiusKm(e.target.value)}
                placeholder="e.g. 5"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-slate-400 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] text-zinc-500 uppercase tracking-wider font-semibold mb-1">
                Start Time (Optional)
              </label>
              <input
                type="datetime-local"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-slate-400 font-sans"
              />
            </div>

            <div>
              <label className="block text-[11px] text-zinc-500 uppercase tracking-wider font-semibold mb-1">
                End Time (Optional)
              </label>
              <input
                type="datetime-local"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-slate-400 font-sans"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-zinc-900 text-white rounded-lg text-xs font-bold hover:bg-zinc-800 transition-colors disabled:opacity-60 cursor-pointer uppercase tracking-wider"
            >
              {loading && <Loader2 size={12} className="animate-spin text-white" />}
              {loading ? "Searching..." : "Execute Buffer Scan"}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          <XCircle size={14} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {results && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card flex items-center justify-between py-4">
              <div>
                <p className="text-[10px] text-zinc-400 uppercase tracking-wider">Total Buffer Hits</p>
                <h3 className="text-2xl font-bold text-zinc-950 mt-1">{results.total_hits}</h3>
              </div>
              <Radio className="text-zinc-300 w-8 h-8" />
            </div>

            <div className="card flex items-center justify-between py-4">
              <div>
                <p className="text-[10px] text-zinc-400 uppercase tracking-wider">Suspects In Area</p>
                <h3 className="text-2xl font-bold text-zinc-950 mt-1">{results.suspects_found.length}</h3>
              </div>
              <Target className="text-zinc-300 w-8 h-8" />
            </div>
          </div>

          {results.suspects_found.length > 0 && (
            <div className="card p-4">
              <span className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold block mb-2">
                Suspects Identified
              </span>
              <div className="flex gap-2 flex-wrap">
                {results.suspects_found.map((name) => (
                  <span
                    key={name}
                    className="px-2.5 py-1 bg-blue-50 border border-blue-100 rounded text-xs font-medium text-blue-800"
                  >
                    {name}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="card">
            <h2 className="text-sm font-semibold text-zinc-900 mb-4">Location Hit Logs</h2>
            {results.hits.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-zinc-400 border-b border-[rgba(59,130,246,0.08)]">
                      <th className="pb-2 font-medium">Suspect</th>
                      <th className="pb-2 font-medium">MSISDN</th>
                      <th className="pb-2 font-medium">Tower ID</th>
                      <th className="pb-2 font-medium text-right">Distance (km)</th>
                      <th className="pb-2 font-medium">Type</th>
                      <th className="pb-2 font-medium text-right">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.hits.map((hit, i) => (
                      <tr key={i} className="table-row-divider">
                        <td className="py-2.5 font-medium text-slate-800">
                          <Link to={`/suspects/${hit.suspect_id}`} className="hover:underline text-blue-600">
                            {hit.suspect_label}
                          </Link>
                        </td>
                        <td className="py-2.5 text-zinc-500 font-mono">{hit.msisdn}</td>
                        <td className="py-2.5 text-zinc-600 font-mono">{hit.tower_id}</td>
                        <td className="py-2.5 text-red-700 font-mono text-right font-semibold">
                          {hit.distance_km} km
                        </td>
                        <td className="py-2.5 text-zinc-500">{hit.call_type}</td>
                        <td className="py-2.5 text-zinc-400 text-right">
                          {new Date(hit.timestamp).toLocaleString("en-IN", {
                            day: "2-digit",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-zinc-400">No pings matched the search parameters.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// AUDIT TRAIL PAGE
export function AuditTrailPage() {
  const [logs, setLogs] = useState<{
    id: string;
    action_type: string;
    entity_type: string;
    entity_id: string | null;
    entity_label: string | null;
    officer_ip: string | null;
    officer_host: string | null;
    detail: Record<string, any>;
    timestamp: string;
  }[]>([]);
  const [total, setTotal] = useState(0);
  const [actionType, setActionType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadLogs = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.getAuditLogs(100, actionType || undefined);
      setLogs(data.logs);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [actionType]);

  const actionTypes = [
    { label: "All Actions", value: "" },
    { label: "Analysis Runs", value: "ANALYSIS_RUN" },
    { label: "Reports Generated", value: "REPORT_GENERATED" },
    { label: "Cases Created", value: "CASE_CREATED" },
    { label: "Suspects Added", value: "SUSPECT_ADDED" },
    { label: "CDR Uploads", value: "CDR_UPLOADED" },
    { label: "IPDR Uploads", value: "IPDR_UPLOADED" },
  ];

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900 flex items-center gap-2">
            <Shield className="text-zinc-800 w-5 h-5 animate-pulse" />
            Officer Activity Audit Trail
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            System logs recording database uploads, analytical computations, and case report compilations ({total} total records).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={actionType}
            onChange={(e) => setActionType(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-slate-400 font-sans cursor-pointer"
          >
            {actionTypes.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <button
            onClick={() => loadLogs()}
            disabled={loading}
            className="p-1.5 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-500 hover:text-slate-900 transition-colors"
            title="Refresh logs"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          <XCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      <div className="card">
        {loading && logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-zinc-400 font-mono text-xs">
            <Loader2 className="animate-spin text-zinc-400 w-6 h-6" />
            <span>Retrieving records...</span>
          </div>
        ) : logs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-zinc-400 border-b border-[rgba(59,130,246,0.08)]">
                  <th className="pb-2 font-medium w-36">Action</th>
                  <th className="pb-2 font-medium">Involved Entity</th>
                  <th className="pb-2 font-medium">Terminal IP</th>
                  <th className="pb-2 font-medium">Details</th>
                  <th className="pb-2 font-medium text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => {
                  let badgeColor = "bg-slate-100 text-slate-700 border-slate-200";
                  if (log.action_type === "ANALYSIS_RUN") badgeColor = "bg-purple-50 text-purple-700 border-purple-100";
                  if (log.action_type === "REPORT_GENERATED") badgeColor = "bg-green-50 text-green-700 border-green-100";
                  if (log.action_type.includes("UPLOADED")) badgeColor = "bg-blue-50 text-blue-700 border-blue-100";

                  return (
                    <tr key={log.id} className="table-row-divider">
                      <td className="py-3 pr-4">
                        <span className={`px-2 py-0.5 rounded border text-[10px] font-mono font-medium ${badgeColor}`}>
                          {log.action_type}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-semibold text-slate-800">
                            {log.entity_label || "Global"}
                          </span>
                          <span className="text-[10px] text-zinc-400 font-mono">
                            {log.entity_type} {log.entity_id ? `(${log.entity_id.slice(0, 8)})` : ""}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 pr-4 font-mono text-zinc-500">
                        {log.officer_ip || "127.0.0.1"}
                      </td>
                      <td className="py-3 pr-4 text-zinc-600 max-w-xs truncate" title={JSON.stringify(log.detail)}>
                        {log.action_type === "ANALYSIS_RUN" ? (
                          <span>
                            Ran {log.detail.engines_run || 8} engines, found {log.detail.events_generated || 0} alerts.
                          </span>
                        ) : log.action_type === "CDR_UPLOADED" || log.action_type === "IPDR_UPLOADED" ? (
                          <span>
                            Inserted {log.detail.rows_inserted || log.detail.rows_inserted_cdr || 0} rows.
                          </span>
                        ) : log.detail.note ? (
                          <span>{String(log.detail.note)}</span>
                        ) : (
                          <span className="font-mono text-[10px] text-zinc-400">
                            {JSON.stringify(log.detail)}
                          </span>
                        )}
                      </td>
                      <td className="py-3 text-zinc-400 text-right">
                        <div className="flex flex-col items-end">
                          <span className="font-medium text-slate-700">
                            {new Date(log.timestamp).toLocaleDateString("en-IN", {
                              day: "2-digit",
                              month: "short",
                              year: "numeric",
                            })}
                          </span>
                          <span className="text-[10px] font-mono mt-0.5">
                            {new Date(log.timestamp).toLocaleTimeString("en-IN", {
                              hour: "2-digit",
                              minute: "2-digit",
                              second: "2-digit",
                            })}
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-zinc-400 py-6 text-center">No audit trail records found.</p>
        )}
      </div>
    </div>
  );
}
