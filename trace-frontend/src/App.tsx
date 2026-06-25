import { Routes, Route, Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import CasesPage from "./pages/CasesPage";
import CaseDetailPage from "./pages/CaseDetailPage";
import UploadPage from "./pages/UploadPage";
import SuspectProfilePage from "./pages/SuspectProfilePage";
import { DashboardPage, SuspectsPage, ReportsPage, SettingsPage, GeoIntelPage, AuditTrailPage } from "./pages/ExtraPages";
import CctvPage from "./pages/CctvPage";
import { api } from "./lib/api";
import type { CaseOut } from "./lib/types";
import {
  LayoutDashboard,
  FolderOpen,
  Users,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  Loader2,
  MapPin,
  Shield,
  Cctv,
} from "lucide-react";

function TraceBootScreen({ onComplete }: { onComplete: () => void }) {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("Initializing secure session...");
  const [mounted, setMounted] = useState(true);

  useEffect(() => {
    const startTime = Date.now();
    const duration = 3500; // 3.5 seconds loading — long enough for user to see

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const pct = Math.min(Math.floor((elapsed / duration) * 100), 100);
      setProgress(pct);

      if (pct < 15) {
        setStatusText("Loading bootloader kernel...");
      } else if (pct < 35) {
        setStatusText("Connecting database subsystem...");
      } else if (pct < 60) {
        setStatusText("Loading geospatial analytical map modules...");
      } else if (pct < 85) {
        setStatusText("Mounting CDR burst anomaly engines...");
      } else if (pct < 98) {
        setStatusText("Verifying investigator session key...");
      } else {
        setStatusText("System ready.");
      }

      if (pct >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          setMounted(false);
          onComplete();
        }, 300);
      }
    }, 16);

    return () => clearInterval(interval);
  }, [onComplete]);

  if (!mounted) return null;

  const isFinished = progress >= 100;

  return (
    <div
      style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "#f8fafc" }}
      className={`flex flex-col items-center justify-center z-[9999] transition-opacity duration-700 ease-in-out ${
        isFinished ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
    >
      {/* Subtle watermark behind — full emblem */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none opacity-[0.035] z-0 overflow-hidden">
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg"
          alt=""
          aria-hidden="true"
          className="w-[70vh] h-[70vh] max-w-[500px] max-h-[500px] object-contain"
        />
      </div>

      <div className="relative z-10 text-center flex flex-col items-center max-w-sm px-6 font-sans">
        {/* Police Emblem */}
        <div className="mb-5 w-[80px] h-[80px] pointer-events-none select-none flex items-center justify-center">
          <img
            src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg"
            alt="Emblem of India"
            className="w-full h-full object-contain"
          />
        </div>

        {/* Prakasham Police identity */}
        <span className="text-[14px] font-semibold tracking-widest text-slate-700 font-sans uppercase">
          Prakasham District Police
        </span>
        <span className="text-[11px] tracking-wider text-slate-400 mt-1 font-sans">
          Andhra Pradesh
        </span>

        {/* Divider */}
        <div className="w-32 h-[1px] bg-slate-200 my-4" />

        <span className="text-[18px] font-bold tracking-[0.18em] text-slate-900 font-mono">
          TRACE
        </span>
        <span className="text-[9px] tracking-[0.12em] text-slate-500 mt-1 text-center uppercase font-mono">
          Investigation System
        </span>

        {/* Progress Bar */}
        <div className="w-64 h-[2px] bg-slate-200 mt-8 overflow-hidden relative rounded-full">
          <div
            style={{ width: `${progress}%` }}
            className="bg-slate-700 h-full transition-all duration-75 ease-linear rounded-full"
          />
        </div>

        <div className="w-64 flex justify-between items-center mt-2.5 font-mono text-[9px] text-slate-400">
          <span className="uppercase tracking-wider">BOOTSTRAP</span>
          <span>{progress}%</span>
        </div>

        {/* Status line */}
        <div className="h-6 mt-4 flex items-center justify-center gap-2 font-mono text-[10px] text-slate-500">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400 shrink-0" />
          <span>{statusText}</span>
        </div>

        {/* Classification label */}
        <div className="mt-8 text-[8px] text-slate-400 tracking-[0.3em] uppercase font-mono">
          RESTRICTED · LAW ENFORCEMENT ONLY
        </div>
      </div>
    </div>
  );
}

function LoginPage({ onLogin }: { onLogin: () => void }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("investigator");
  const [password, setPassword] = useState("PrakasamPolice_2026!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    setLoading(true);
    setError("");

    setTimeout(() => {
      if (username === "investigator" && password === "PrakasamPolice_2026!") {
        localStorage.setItem("trace_logged_in", "true");
        onLogin();
        navigate("/");
      } else {
        setError("Invalid secure credentials.");
      }
      setLoading(false);
    }, 800);
  };

  return (
    <div
      style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "#f8fafc" }}
      className="flex flex-col z-[999] overflow-hidden font-sans"
    >
      {/* Subtle watermark — full emblem */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none opacity-[0.035] z-0 overflow-hidden">
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg"
          alt=""
          aria-hidden="true"
          className="w-[70vh] h-[70vh] max-w-[500px] max-h-[500px] object-contain"
        />
      </div>

      {/* Top Header bar */}
      <div className="relative z-10 w-full border-b border-slate-200 bg-white/80 backdrop-blur-sm px-8 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          {/* small emblem */}
          <div className="w-7 h-7 pointer-events-none select-none flex items-center justify-center">
            <img
              src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg"
              alt=""
              aria-hidden="true"
              className="w-full h-full object-contain"
            />
          </div>
          <span className="text-slate-800 text-sm font-semibold tracking-[0.1em] font-mono">TRACE</span>
          <span className="text-slate-400 text-[9px] uppercase tracking-wider hidden sm:block">· Criminal Investigation Platform</span>
        </div>
        <span className="text-[9px] text-slate-400 font-mono uppercase tracking-wider">SECURE LOGIN</span>
      </div>

      {/* Center Login Card */}
      <div className="relative z-10 flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-[380px]">
          {/* Emblem + Title above form */}
          <div className="flex flex-col items-center mb-7">
            {/* Full emblem */}
            <div className="w-[90px] h-[90px] pointer-events-none select-none mb-4 flex items-center justify-center">
              <img
                src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg"
                alt="Emblem of India"
                className="w-full h-full object-contain"
              />
            </div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-[0.12em] font-sans">TRACE</h1>
            <p className="text-[10px] text-slate-500 mt-1.5 uppercase tracking-[0.18em] text-center font-mono leading-relaxed">
              Telecom Record Analysis<br />for Criminal Examination
            </p>
          </div>

          {/* Login form card */}
          <div className="bg-white/95 border border-slate-200/80 rounded p-6 space-y-4 shadow-sm backdrop-blur-sm">
            <div className="text-[9px] text-slate-400 uppercase tracking-[0.2em] font-mono pb-3 border-b border-slate-100">
              Authentication Portal · Restricted System
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-600 flex items-center gap-2 font-mono">
                <ShieldAlert size={13} className="shrink-0" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] font-semibold text-slate-500 uppercase tracking-[0.2em]">Credential ID</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. investigator"
                  autoComplete="username"
                  className="w-full bg-slate-50 border border-slate-200 rounded-sm px-3 py-2.5 text-xs text-slate-800 focus:outline-none focus:border-slate-400 font-mono placeholder-slate-300 transition-colors"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[9px] font-semibold text-slate-500 uppercase tracking-[0.2em]">Access Passphrase</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="w-full bg-slate-50 border border-slate-200 rounded-sm px-3 py-2.5 text-xs text-slate-800 focus:outline-none focus:border-slate-400 font-mono placeholder-slate-300 transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-1 py-3 bg-slate-900 text-white rounded-sm text-xs font-bold hover:bg-slate-800 transition-colors flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer tracking-[0.15em] uppercase shadow-sm"
              >
                {loading && <Loader2 size={12} className="animate-spin text-white" />}
                {loading ? "Authenticating..." : "Authenticate Session"}
              </button>
            </form>
          </div>

          {/* Footer */}
          <div className="mt-5 text-center space-y-1">
            <p className="text-[9px] text-slate-400 uppercase tracking-[0.2em] font-mono">
              RESTRICTED ACCESS · LAW ENFORCEMENT ONLY
            </p>
            <p className="text-[8px] text-slate-400 font-mono">
              IP logged · Sec 70B IT Act applies
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function NavBar({ onLogout }: { onLogout: () => void }) {
  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-zinc-200 px-6 py-0 flex items-center justify-between h-12 shrink-0 font-sans">
      <div className="flex items-center gap-3">
        <img
          src="/prakasham-police.png"
          alt="Prakasham District Police"
          className="h-7 w-7 object-contain opacity-90"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
        <Link to="/" className="flex flex-col">
          <span className="text-zinc-900 font-semibold text-[20px] leading-tight tracking-tight">TRACE</span>
        </Link>
        <div className="h-6 w-[1px] bg-zinc-200" />
        <span className="text-[10px] text-zinc-700 font-bold uppercase tracking-wider">
          Prakasham District Police
        </span>
        <span className="text-[9px] text-zinc-400 uppercase tracking-wide font-mono hidden md:block">
          · Criminal Investigation Dept, AP
        </span>
      </div>
      <div className="flex items-center gap-4 text-xs font-mono">
        <span className="text-zinc-600 bg-zinc-100 border border-zinc-200 px-2.5 py-1 rounded">
          Session: Inspector Sharma
        </span>
        <button
          onClick={onLogout}
          className="text-zinc-500 hover:text-zinc-900 px-3 py-1 border border-zinc-200 hover:bg-zinc-50 rounded transition-colors cursor-pointer"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}

function IconRail({
  isCollapsed,
  setIsCollapsed,
}: {
  isCollapsed: boolean;
  setIsCollapsed: (v: boolean) => void;
}) {
  const loc = useLocation();

  const navItems = [
    { label: "Dashboard", path: "/", icon: LayoutDashboard },
    { label: "Cases", path: "/cases", icon: FolderOpen },
    { label: "Suspects", path: "/suspects", icon: Users },
    { label: "CCTV Plugin", path: "/cctv", icon: Cctv },
    { label: "Reports", path: "/reports", icon: FileText },
    { label: "Geo Intel", path: "/geo-intel", icon: MapPin },
    { label: "Audit Trail", path: "/audit", icon: Shield },
    { label: "Settings", path: "/settings", icon: Settings },
  ];

  const isLinkActive = (path: string) => {
    if (path === "/") {
      return loc.pathname === "/";
    }
    if (path === "/cases") {
      return loc.pathname === "/cases" || loc.pathname.startsWith("/cases/");
    }
    if (path === "/suspects") {
      return loc.pathname.startsWith("/suspects");
    }
    return loc.pathname === path;
  };

  return (
    <div className="w-[52px] bg-gray-900 flex flex-col justify-between items-center py-4 h-full shrink-0 z-20">
      <div className="flex flex-col items-center gap-6 w-full">
        {navItems.map((item) => {
          const active = isLinkActive(item.path);
          return (
            <div key={item.label} className="relative group w-full flex justify-center">
             <Link
                to={item.path}
                className={`w-full py-2 flex items-center justify-center border-l-2 transition-all ${
                  active
                    ? "text-blue-400 border-l-blue-500 bg-gray-800/50"
                    : "text-gray-400 border-l-transparent hover:text-gray-200 hover:bg-gray-800"
                }`}
              >
                <item.icon className="w-5 h-5" />
              </Link>
              {/* Tooltip */}
              <div className="absolute left-full ml-2 px-2 py-1 bg-slate-950 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 shadow-md">
                {item.label}
              </div>
            </div>
          );
        })}
      </div>

      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full py-2 flex items-center justify-center text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-all border-l-2 border-l-transparent"
      >
        {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
      </button>
    </div>
  );
}

function Sidebar({
  isCollapsed,
  recentCases,
  hasHighSeverityMap,
}: {
  isCollapsed: boolean;
  recentCases: CaseOut[];
  hasHighSeverityMap: Record<string, boolean>;
}) {
  const navigate = useNavigate();

  return (
    <div
      style={{ width: isCollapsed ? "0px" : "220px" }}
      className="bg-white border-r border-slate-200 flex flex-col overflow-hidden transition-all duration-200 h-full shrink-0 z-10"
    >
      <div className="text-xs font-semibold text-slate-400 tracking-widest px-4 pt-5 pb-2">
        ACTIVE CASES
      </div>
      <div className="flex flex-col gap-2 px-3 overflow-y-auto pb-4 flex-1">
        {recentCases.map((c) => {
          const hasHigh = hasHighSeverityMap[c.id];
          return (
            <button
              key={c.id}
              onClick={() => navigate(`/cases/${c.id}`)}
              className="w-full text-left p-2.5 border border-slate-200 rounded-lg hover:border-blue-200 transition-colors flex flex-col gap-1 relative bg-white"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-800 truncate" title={c.name}>
                  {c.name}
                </span>
                {hasHigh && (
                  <span className="w-2 h-2 rounded-full bg-red-600 shrink-0 mt-1" />
                )}
              </div>
              <span className="text-xs text-slate-500">
                {c.suspect_count} suspect{c.suspect_count !== 1 ? "s" : ""} · {c.event_count} event{c.event_count !== 1 ? "s" : ""}
              </span>
            </button>
          );
        })}
        {recentCases.length === 0 && (
          <span className="text-xs text-slate-400 px-2">No active cases.</span>
        )}
      </div>
      {/* Prakasham Police sidebar footer */}
      <div className="border-t border-slate-200 p-3 shrink-0">
        <p className="text-[9px] font-mono font-semibold text-slate-400 uppercase tracking-wide">
          Prakasham Dist. Police
        </p>
        <p className="text-[9px] text-slate-300 mt-0.5">
          AP Criminal Investigation Dept.
        </p>
      </div>
    </div>
  );
}

export default function App() {
  const loc = useLocation();
  const [booting, setBooting] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [recentCases, setRecentCases] = useState<CaseOut[]>([]);
  const [hasHighSeverityMap, setHasHighSeverityMap] = useState<Record<string, boolean>>({});
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    return localStorage.getItem("trace_logged_in") === "true";
  });

  const handleLogout = () => {
    localStorage.removeItem("trace_logged_in");
    setIsLoggedIn(false);
  };

  const loadRecentCases = async () => {
    try {
      const allCases = await api.getCases();
      const top3 = allCases.slice(0, 3);
      setRecentCases(top3);

      top3.forEach(async (c) => {
        try {
          const events = await api.getEvents(c.id, undefined, "HIGH");
          setHasHighSeverityMap((prev) => ({ ...prev, [c.id]: events.length > 0 }));
        } catch (e) {
          console.error(e);
        }
      });
    } catch (err) {
      console.error("Failed to load recent cases:", err);
    }
  };

  useEffect(() => {
    if (isLoggedIn) {
      loadRecentCases();
    }
  }, [loc.pathname, isLoggedIn]);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-zinc-50 font-sans relative">
      {/* Boot loader always runs first */}
      {booting && <TraceBootScreen onComplete={() => setBooting(false)} />}

      {/* If boot loading is complete, check session */}
      {!booting && (
        !isLoggedIn ? (
          <LoginPage onLogin={() => setIsLoggedIn(true)} />
        ) : (
          <div className="h-full flex flex-col overflow-hidden">
            <NavBar onLogout={handleLogout} />

            <div className="flex-1 flex overflow-hidden">
              <IconRail isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />

              <Sidebar
                isCollapsed={isCollapsed}
                recentCases={recentCases}
                hasHighSeverityMap={hasHighSeverityMap}
              />

              <div className="flex-1 overflow-y-auto relative bg-zinc-50 main-area">
                {/* Indian Police Emblem watermark — fixed to viewport so it never clips */}
                <div
                  className="pointer-events-none select-none fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[70vh] h-[70vh] max-w-[500px] max-h-[500px] opacity-[0.055] z-0 overflow-hidden flex items-center justify-center"
                  style={{ marginLeft: "88px" }}  
                >
                  <img
                    src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg"
                    alt=""
                    aria-hidden="true"
                    className="w-full h-full object-contain"
                  />
                </div>

                <div className="relative z-10">
                  <Routes>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/cases" element={<CasesPage />} />
                    <Route path="/cases/:caseId" element={<CaseDetailPage />} />
                    <Route path="/cases/:caseId/upload" element={<UploadPage />} />
                    <Route path="/suspects/:suspectId" element={<SuspectProfilePage />} />
                    <Route path="/suspects" element={<SuspectsPage />} />
                    <Route path="/cctv" element={<CctvPage />} />
                    <Route path="/reports" element={<ReportsPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/geo-intel" element={<GeoIntelPage />} />
                    <Route path="/audit" element={<AuditTrailPage />} />
                  </Routes>
                </div>
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
}
