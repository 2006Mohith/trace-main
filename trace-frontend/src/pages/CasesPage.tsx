import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import type { CaseOut } from "../lib/types";
import { Plus, Folder, Calendar, Users, AlertTriangle, Trash2 } from "lucide-react";

function formatDate(s: string) {
  return new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export default function CasesPage() {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [caseName, setCaseName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    api.getCases()
      .then(setCases)
      .catch(() => setError("Failed to connect to TRACE backend. Is the server running?"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseName.trim()) return;
    setCreating(true);
    try {
      const created = await api.createCase(caseName.trim());
      setCases((prev) => [created, ...prev]);
      setCaseName("");
      setShowForm(false);
    } catch (err: unknown) {
      setError(String(err));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this case? All suspect data, uploaded files, and analysis events will be permanently deleted.")) {
      return;
    }
    try {
      await api.deleteCase(id);
      setCases((prev) => prev.filter((c) => c.id !== id));
    } catch (err: unknown) {
      alert("Failed to delete case: " + String(err));
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 mb-1">Investigation Cases</h1>
          {/* Upgrade 1: Prakasham District Police branding row */}
          <div className="flex items-center gap-2 mt-1 mb-1">
            {/* Place Prakasham District Police logo at /public/prakasham-police.png */}
            <img
              src="/prakasham-police.png"
              alt="Prakasham District Police"
              className="h-8 object-contain opacity-80"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
            <span className="text-[12px] text-slate-500">
              Prakasham District Police — Criminal Intelligence Division
            </span>
          </div>
          <p className="text-sm text-zinc-500">
            {cases.length} active {cases.length === 1 ? "case" : "cases"}
          </p>
        </div>
        <button
          id="btn-new-case"
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white rounded-lg text-sm font-medium hover:bg-zinc-700 transition-colors"
        >
          <Plus size={15} />
          New Case
        </button>
      </div>

      {/* Inline create form */}
      {showForm && (
        <div className="card mb-6">
          <h2 className="text-sm font-semibold text-zinc-900 mb-3">New Investigation Case</h2>
          <form onSubmit={handleCreate} className="flex gap-3 items-center">
            <input
              id="input-case-name"
              type="text"
              value={caseName}
              onChange={(e) => setCaseName(e.target.value)}
              placeholder="e.g. Operation Sandstorm"
              className="flex-1 border border-zinc-200 rounded-lg px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:border-transparent"
              autoFocus
            />
            <button
              id="btn-create-case"
              type="submit"
              disabled={creating || !caseName.trim()}
              className="px-4 py-2 bg-zinc-900 text-white rounded-lg text-sm font-medium disabled:opacity-40 hover:bg-zinc-700 transition-colors"
            >
              {creating ? "Creating…" : "Create Case"}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 border border-zinc-200 rounded-lg text-sm text-zinc-600 hover:bg-zinc-50 transition-colors"
            >
              Cancel
            </button>
          </form>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle size={15} />
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card border border-slate-200 text-left">
              <div className="flex items-start justify-between mb-4">
                <div className="w-48 h-4 bg-slate-200 rounded animate-pulse" />
              </div>
              <div className="w-32 h-3 bg-slate-100 rounded animate-pulse mt-2" />
              <div className="flex items-center gap-4 mt-4">
                <div className="w-20 h-3 bg-slate-100 rounded animate-pulse" />
                <div className="w-20 h-3 bg-slate-100 rounded animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      ) : cases.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-center">
          <Folder size={32} className="text-zinc-300 mb-3" />
          <p className="text-zinc-500 text-sm">No cases yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {cases.map((c) => (
            <div
              key={c.id}
              id={`case-card-${c.id}`}
              onClick={() => navigate(`/cases/${c.id}`)}
              className="card border border-slate-200 text-left hover:border-blue-200 hover:shadow-sm transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between mb-4">
                  <h2 className="text-[15px] font-semibold text-zinc-900 group-hover:text-zinc-700 transition-colors line-clamp-2 pr-2">
                    {c.name}
                  </h2>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] font-mono text-zinc-400 bg-zinc-50 border border-zinc-150 rounded px-1.5 py-0.5">{c.id.slice(0, 8)}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(c.id);
                      }}
                      className="p-1.5 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                      title="Delete Case"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs text-zinc-500 mt-2">
                <span className="flex items-center gap-1">
                  <Calendar size={12} />
                  {formatDate(c.created_at)}
                </span>
                <span className="flex items-center gap-1">
                  <Users size={12} />
                  {c.suspect_count} suspect{c.suspect_count !== 1 ? "s" : ""}
                </span>
                {c.event_count > 0 && (
                  <span className="flex items-center gap-1 text-red-600">
                    <AlertTriangle size={12} />
                    {c.event_count} event{c.event_count !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
