import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import FileUploadZone from "../components/FileUploadZone";
import { CheckCircle, Download } from "lucide-react";

export default function UploadPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [label, setLabel] = useState("");
  const [cdrFile, setCdrFile] = useState<File | null>(null);
  const [ipdrFile, setIpdrFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ suspectLabel: string; cdr: number; ipdr: number; suspectId: string } | null>(null);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !cdrFile || !label.trim()) return;
    setUploading(true);
    setError("");
    try {
      const res = await api.uploadRecords(caseId, label.trim(), cdrFile, ipdrFile || undefined);
      setResult({ suspectLabel: label.trim(), cdr: res.rows_inserted_cdr, ipdr: res.rows_inserted_ipdr, suspectId: res.suspect_id });
      setLabel("");
      setCdrFile(null);
      setIpdrFile(null);
    } catch (err: unknown) {
      setError(String(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto px-6 py-8">
      <Link to={`/cases/${caseId}`} className="text-xs text-zinc-400 hover:text-zinc-600 transition-colors mb-4 block">
        ← Back to Case
      </Link>

      <h1 className="text-xl font-semibold text-zinc-900 mb-1">Upload Records</h1>
      <p className="text-sm text-zinc-500 mb-6">Add CDR and IPDR data for a new suspect.</p>

      {/* Success state */}
      {result && (
        <div className="card mb-6 border-green-200 bg-green-50">
          <div className="flex items-start gap-3">
            <CheckCircle size={18} className="text-green-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-green-900 mb-0.5">Upload successful</p>
              <p className="text-sm text-green-800">
                <span className="font-medium">{result.suspectLabel}</span> uploaded.{" "}
                {result.cdr} CDR rows, {result.ipdr} IPDR rows ingested.
              </p>
              <div className="flex gap-3 mt-3">
                <Link
                  to={`/cases/${caseId}`}
                  className="text-xs text-green-700 underline underline-offset-2"
                >
                  ← Back to case
                </Link>
                <button
                  className="text-xs text-green-700 underline underline-offset-2"
                  onClick={() => setResult(null)}
                >
                  Upload another suspect
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {!result && (
        <form onSubmit={handleSubmit} className="card space-y-5">
          {/* Suspect Label */}
          <div>
            <label htmlFor="suspect-label" className="block text-xs font-medium text-zinc-700 mb-1.5">
              Suspect Label <span className="text-red-500">*</span>
            </label>
            <input
              id="suspect-label"
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Suspect A"
              className="w-full border border-zinc-200 rounded-lg px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:border-transparent"
              required
            />
          </div>

          {/* CDR File */}
          <div>
            <label className="block text-xs font-medium text-zinc-700 mb-1.5">
              CDR File (.csv) <span className="text-red-500">*</span>
            </label>
            <FileUploadZone
              id="cdr-upload"
              file={cdrFile}
              onFile={setCdrFile}
              accept=".csv"
            />
          </div>

          {/* IPDR File */}
          <div>
            <label className="block text-xs font-medium text-zinc-700 mb-1.5">
              IPDR File (.csv) <span className="text-zinc-400 font-normal">— Optional</span>
            </label>
            <FileUploadZone
              id="ipdr-upload"
              file={ipdrFile}
              onFile={setIpdrFile}
              accept=".csv"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
          )}

          <button
            id="btn-upload-submit"
            type="submit"
            disabled={uploading || !cdrFile || !label.trim()}
            className="w-full py-2.5 bg-zinc-900 text-white rounded-lg text-sm font-medium disabled:opacity-40 hover:bg-zinc-700 transition-colors"
          >
            {uploading ? "Uploading…" : "Upload Records"}
          </button>
        </form>
      )}

      {/* Template downloads */}
      <div className="mt-6 flex gap-4">
        <a
          href={api.getCdrTemplateUrl()}
          download="cdr_template.csv"
          id="download-cdr-template"
          className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-900 transition-colors"
        >
          <Download size={12} />
          CDR template
        </a>
        <a
          href={api.getIpdrTemplateUrl()}
          download="ipdr_template.csv"
          id="download-ipdr-template"
          className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-900 transition-colors"
        >
          <Download size={12} />
          IPDR template
        </a>
      </div>

      {/* Column reference */}
      <div className="mt-6 p-4 bg-zinc-50 rounded-lg border border-zinc-100">
        <p className="text-xs font-medium text-zinc-600 mb-2">Required CDR columns:</p>
        <p className="text-xs font-mono text-zinc-500 leading-relaxed">
          msisdn_a, msisdn_b, imei, tower_id, tower_lat, tower_lon, call_type, duration_sec, timestamp
        </p>
        <p className="text-xs font-medium text-zinc-600 mb-2 mt-3">Required IPDR columns:</p>
        <p className="text-xs font-mono text-zinc-500">
          msisdn, dest_ip, dest_port, data_volume_kb, timestamp
        </p>
      </div>
    </div>
  );
}
