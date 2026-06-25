import { useEffect, useState } from "react";
import { api } from "../lib/api";
import {
  Camera,
  Plus,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Eye,
  Activity,
  MapPin,
  Upload,
  ShieldCheck,
  Cpu,
  Tv,
  Loader2,
} from "lucide-react";

export default function CctvPage() {
  const [cameras, setCameras] = useState<any[]>([]);
  const [sightings, setSightings] = useState<any[]>([]);
  const [loadingCameras, setLoadingCameras] = useState(true);
  const [loadingSightings, setLoadingSightings] = useState(true);
  
  // Camera Form
  const [showCamForm, setShowCamForm] = useState(false);
  const [cameraId, setCameraId] = useState("");
  const [locationName, setLocationName] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [rtspUrl, setRtspUrl] = useState("");
  const [registering, setRegistering] = useState(false);
  const [formError, setFormError] = useState("");

  // Media Matching Form
  const [matchingFile, setMatchingFile] = useState<File | null>(null);
  const [sampleRate, setSampleRate] = useState(15);
  const [analyzing, setAnalyzing] = useState(false);
  const [matchResult, setMatchResult] = useState<any | null>(null);
  const [matchError, setMatchError] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Status updates
  const [updatingCameraId, setUpdatingCameraId] = useState<string | null>(null);

  // Load cameras
  const loadCameras = () => {
    setLoadingCameras(true);
    api.getCameras()
      .then(setCameras)
      .catch((e) => console.error("Failed to load cameras", e))
      .finally(() => setLoadingCameras(false));
  };

  // Load sightings
  const loadSightings = () => {
    setLoadingSightings(true);
    api.getRecentSightings(30)
      .then(setSightings)
      .catch((e) => console.error("Failed to load sightings", e))
      .finally(() => setLoadingSightings(false));
  };

  useEffect(() => {
    loadCameras();
    loadSightings();
  }, []);

  const handleCameraRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cameraId.trim() || !locationName.trim() || !latitude.trim() || !longitude.trim()) {
      setFormError("All fields except RTSP URL are required.");
      return;
    }
    setRegistering(true);
    setFormError("");
    try {
      await api.registerCamera({
        camera_id: cameraId.trim(),
        location_name: locationName.trim(),
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        rtsp_url: rtspUrl.trim() || "rtsp://localhost:554/live"
      });
      
      setCameraId("");
      setLocationName("");
      setLatitude("");
      setLongitude("");
      setRtspUrl("");
      setShowCamForm(false);
      loadCameras();
    } catch (err: any) {
      setFormError(err.message || "Failed to register camera.");
    } finally {
      setRegistering(false);
    }
  };

  const handleCameraStatusToggle = async (camId: string, currentStatus: string) => {
    setUpdatingCameraId(camId);
    const nextStatus = currentStatus === "ONLINE" ? "OFFLINE" : currentStatus === "OFFLINE" ? "MAINTENANCE" : "ONLINE";
    try {
      await api.updateCameraStatus(camId, nextStatus);
      loadCameras();
    } catch (e) {
      console.error(e);
      alert("Failed to update status.");
    } finally {
      setUpdatingCameraId(null);
    }
  };

  const handleMediaMatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!matchingFile) return;
    setAnalyzing(true);
    setMatchError("");
    setMatchResult(null);

    try {
      const res = await api.matchMedia(matchingFile, sampleRate);
      setMatchResult(res);
      loadSightings();
    } catch (err: any) {
      setMatchError(err.message || "Media analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSightingVerify = async (sightingId: string) => {
    try {
      await api.verifySighting(sightingId, true, "Visual inspection confirmed matches.");
      // Refresh local state list
      setSightings((prev) =>
        prev.map((s) => (s.id === sightingId ? { ...s, is_verified: true } : s))
      );
    } catch (e) {
      console.error(e);
      alert("Failed to verify sighting.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setMatchingFile(file);
      setMatchResult(null);
      setMatchError("");
      
      // Cleanup old preview
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const activeCameras = cameras.filter((c) => c.status === "ONLINE").length;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      
      {/* ══ HEADER ══ */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-zinc-200 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <Tv className="w-6 h-6 text-zinc-900" />
            <h1 className="text-2xl font-bold text-zinc-900">CCTV Live Surveillance Analysis</h1>
          </div>
          <div className="flex items-center gap-2 mt-1.5">
            <img
              src="/prakasham-police.png"
              alt="Prakasham District Police"
              className="h-8 object-contain opacity-80"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
            <span className="text-[12px] text-slate-500">
              Prakasham District Police — Real-time Facial Surveillance Control
            </span>
          </div>
        </div>
        
        {/* Quick Stats */}
        <div className="flex items-center gap-4 mt-4 md:mt-0 text-xs font-mono">
          <div className="bg-white border border-zinc-200 px-3 py-2 rounded shadow-sm flex items-center gap-2">
            <Activity className={`w-3.5 h-3.5 ${activeCameras > 0 ? "text-emerald-500 animate-pulse" : "text-zinc-400"}`} />
            <span>Cameras: <strong>{activeCameras}/{cameras.length} Online</strong></span>
          </div>
          <div className="bg-white border border-zinc-200 px-3 py-2 rounded shadow-sm flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-zinc-700" />
            <span>Sightings: <strong>{sightings.length} Logged</strong></span>
          </div>
          <button
            onClick={() => { loadCameras(); loadSightings(); }}
            className="p-2 border border-zinc-200 bg-white hover:bg-zinc-50 rounded shadow-sm transition-colors cursor-pointer"
            title="Refresh Feed"
          >
            <RefreshCw className="w-3.5 h-3.5 text-zinc-500" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* ══ COLUMN 1 & 2: LIVE SURVEILLANCE & UPLOAD ANALYZER ══ */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Section: Upload & Analyze */}
          <div className="bg-white/80 backdrop-blur-sm border border-zinc-200 rounded-md p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <h2 className="text-sm font-bold text-zinc-800 flex items-center gap-2">
                <Upload className="w-4 h-4 text-zinc-500" />
                Upload Image / Video for Face Match
              </h2>
              <span className="text-[10px] bg-zinc-100 text-zinc-600 px-2 py-0.5 rounded font-mono">
                SECURE STREAM INGEST
              </span>
            </div>

            <form onSubmit={handleMediaMatch} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
              <div className="md:col-span-2 flex flex-col gap-1.5">
                <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                  Select Media File (JPEG, PNG, MP4, AVI)
                </label>
                <input
                  type="file"
                  accept="image/*,video/*"
                  onChange={handleFileChange}
                  className="w-full text-xs text-zinc-500 file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-zinc-900 file:text-white hover:file:bg-zinc-700 file:cursor-pointer"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                  Video Frame Sample Rate
                </label>
                <select
                  value={sampleRate}
                  onChange={(e) => setSampleRate(Number(e.target.value))}
                  className="w-full bg-zinc-50 border border-zinc-200 rounded px-2.5 py-1.5 text-xs text-zinc-700"
                >
                  <option value={5}>Every 5th frame (Slow)</option>
                  <option value={15}>Every 15th frame (Standard)</option>
                  <option value={30}>Every 30th frame (Fast)</option>
                </select>
              </div>

              <div className="md:col-span-3 flex justify-end">
                <button
                  type="submit"
                  disabled={analyzing || !matchingFile}
                  className="flex items-center gap-2 px-5 py-2 bg-zinc-950 text-white rounded text-xs font-bold hover:bg-zinc-800 disabled:opacity-50 disabled:hover:bg-zinc-950 transition-colors shadow-sm cursor-pointer"
                >
                  {analyzing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Cpu className="w-3.5 h-3.5" />}
                  {analyzing ? "Analyzing Frames..." : "Run Facial Recognition"}
                </button>
              </div>
            </form>

            {matchError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-xs flex items-center gap-2 font-mono">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                {matchError}
              </div>
            )}

            {/* Preview Area */}
            {previewUrl && !matchResult && !analyzing && (
              <div className="border border-zinc-200 rounded p-2 bg-zinc-50 flex justify-center max-h-[300px] overflow-hidden">
                {matchingFile?.type.startsWith("image/") ? (
                  <img src={previewUrl} alt="Preview" className="max-h-[280px] object-contain" />
                ) : (
                  <video src={previewUrl} controls className="max-h-[280px] object-contain" />
                )}
              </div>
            )}

            {/* Analysis Loading State */}
            {analyzing && (
              <div className="flex flex-col items-center justify-center py-12 border border-zinc-200 border-dashed rounded bg-zinc-50/50 space-y-3">
                <Loader2 className="w-7 h-7 text-zinc-900 animate-spin" />
                <span className="text-xs text-zinc-500 font-mono">Decoding frames and extracting facial vectors...</span>
              </div>
            )}

            {/* Match Results Display */}
            {matchResult && (
              <div className="space-y-4 border border-zinc-200 rounded p-4 bg-zinc-50">
                <h3 className="text-xs font-bold text-zinc-700 uppercase tracking-wider font-mono">
                  Analysis Report · SHA256: {matchResult.image_hash?.substring(0, 16)}...
                </h3>

                {matchResult.type === "image" && (
                  <div className="space-y-4">
                    <div className="flex flex-col md:flex-row gap-4">
                      {/* Image Preview */}
                      <div className="border border-zinc-200 rounded p-1 bg-white flex justify-center items-center shrink-0 w-full md:w-[220px]">
                        <img src={previewUrl || ""} alt="Match preview" className="max-h-[160px] object-contain" />
                      </div>

                      {/* Match Details list */}
                      <div className="flex-1 space-y-3">
                        <div className="text-xs text-zinc-500">
                          Detected <strong>{matchResult.total_faces_detected}</strong> face(s) in image.
                        </div>

                        {matchResult.results?.map((res: any, idx: number) => (
                          <div key={idx} className="bg-white border border-zinc-200 rounded p-3 text-xs space-y-2">
                            <div className="flex justify-between items-center border-b border-zinc-100 pb-1.5">
                              <span className="font-semibold text-zinc-700 font-mono">Face #{idx + 1}</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                                res.match_confidence === "CONFIRMED" ? "bg-emerald-100 text-emerald-800" :
                                res.match_confidence === "PROBABLE" ? "bg-blue-100 text-blue-800" :
                                res.match_confidence === "POSSIBLE" ? "bg-amber-100 text-amber-800" :
                                "bg-zinc-100 text-zinc-600"
                              }`}>
                                {res.match_confidence}
                              </span>
                            </div>

                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div>
                                <span className="text-zinc-400">Suspect Label:</span>{" "}
                                <strong className="text-zinc-800">{res.suspect_label || "No Match"}</strong>
                              </div>
                              <div>
                                <span className="text-zinc-400">Match Confidence:</span>{" "}
                                <strong className="text-zinc-800">{res.confidence_percent ? `${res.confidence_percent}%` : "0%"}</strong>
                              </div>
                              <div>
                                <span className="text-zinc-400">Liveness State:</span>{" "}
                                <strong className={`font-mono ${res.is_live ? "text-emerald-600" : "text-rose-600 font-bold"}`}>
                                  {res.is_live ? "LIVE" : "SPOOF / SCREEN"}
                                </strong>
                              </div>
                              <div>
                                <span className="text-zinc-400">Liveness Score:</span>{" "}
                                <strong className="text-zinc-800">{res.liveness_score ? `${res.liveness_score.toFixed(1)}%` : "0%"}</strong>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {matchResult.type === "video" && (
                  <div className="space-y-3">
                    <div className="text-xs text-zinc-500">
                      Processed video (FPS: {matchResult.video_metadata?.fps}, Duration: {matchResult.video_metadata?.duration_sec}s). 
                      Found <strong>{matchResult.unique_sightings}</strong> suspect match sequence(s).
                    </div>

                    <div className="space-y-2">
                      {matchResult.sightings?.map((s: any, idx: number) => (
                        <div key={idx} className="bg-white border border-zinc-200 rounded p-3 text-xs flex gap-4 items-center">
                          {/* Face Thumbnail */}
                          {s.frame_thumbnails && s.frame_thumbnails[0] && (
                            <img
                              src={`data:image/jpeg;base64,${s.frame_thumbnails[0]}`}
                              alt="thumbnail"
                              className="w-14 h-14 object-cover rounded border border-zinc-200 shrink-0"
                            />
                          )}
                          <div className="flex-1 grid grid-cols-2 md:grid-cols-3 gap-2">
                            <div>
                              <span className="text-zinc-400">Suspect:</span>{" "}
                              <strong className="text-zinc-800">{s.suspect_label}</strong>
                            </div>
                            <div>
                              <span className="text-zinc-400">First Seen:</span>{" "}
                              <strong className="text-zinc-800 font-mono">{s.first_seen_sec}s</strong>
                            </div>
                            <div>
                              <span className="text-zinc-400">Last Seen:</span>{" "}
                              <strong className="text-zinc-800 font-mono">{s.last_seen_sec}s</strong>
                            </div>
                            <div className="col-span-2 md:col-span-3">
                              <span className="text-zinc-400">Peak Confidence:</span>{" "}
                              <strong className="text-emerald-600 font-mono">{s.max_confidence.toFixed(1)}% ({s.match_category || "PROBABLE"})</strong>
                            </div>
                          </div>
                        </div>
                      ))}

                      {matchResult.unique_sightings === 0 && (
                        <div className="p-4 text-center text-zinc-400 text-xs">
                          No matching registered suspects found in video frames.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* CCTV Camera Stream Feed Simulators */}
          <div className="bg-white/80 backdrop-blur-sm border border-zinc-200 rounded-md p-5 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-zinc-800 flex items-center gap-2">
              <Camera className="w-4 h-4 text-zinc-500" />
              Live CCTV Stream Feed
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {cameras.slice(0, 2).map((c) => (
                <div key={c.id} className="relative rounded overflow-hidden aspect-video border border-zinc-300 bg-zinc-950 group">
                  {/* Status label */}
                  <span className="absolute top-2.5 left-2.5 bg-black/60 backdrop-blur-sm text-[9px] text-zinc-300 font-mono px-2 py-0.5 rounded flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${c.status === "ONLINE" ? "bg-emerald-500 animate-pulse" : "bg-red-500"}`} />
                    {c.camera_id} · {c.location_name}
                  </span>
                  
                  {/* Scanning scanline overlay */}
                  {c.status === "ONLINE" && (
                    <div className="absolute inset-0 pointer-events-none bg-gradient-to-b from-transparent via-white/5 to-transparent bg-[length:100%_4px] animate-[scanline_8s_linear_infinite]" />
                  )}

                  {c.status === "ONLINE" ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4">
                      {/* Scanning visual overlay */}
                      <Activity className="w-8 h-8 text-emerald-400/40 animate-pulse mb-2" />
                      <span className="text-[10px] text-emerald-400/50 font-mono tracking-wider">LIVE RECORD FEED ACTIVE</span>
                      <span className="text-[8px] text-zinc-500 font-mono mt-0.5">RTSP PROTOCOL DECODE ENABLED</span>
                    </div>
                  ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center bg-zinc-900/90 text-zinc-500">
                      <AlertTriangle className="w-7 h-7 mb-2 text-zinc-600" />
                      <span className="text-[10px] font-mono uppercase">Camera Status: {c.status}</span>
                    </div>
                  )}
                </div>
              ))}

              {cameras.length === 0 && (
                <div className="col-span-2 py-8 text-center text-zinc-400 text-xs border border-zinc-200 border-dashed rounded bg-zinc-50/50">
                  No active CCTV cameras registered in system.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ══ COLUMN 3: SIGHTINGS & CAMERAS REGISTRY ══ */}
        <div className="space-y-6">
          
          {/* Section: Sighting feed */}
          <div className="bg-white/80 backdrop-blur-sm border border-zinc-200 rounded-md p-5 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-zinc-800 flex items-center justify-between border-b border-zinc-100 pb-3">
              <span className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-zinc-500" />
                Recent Face Sightings
              </span>
              <button onClick={loadSightings} className="text-[10px] text-blue-500 hover:text-blue-700 font-mono">
                Refresh
              </button>
            </h2>

            <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
              {sightings.map((sig) => (
                <div key={sig.id} className="bg-zinc-50/80 border border-zinc-200 rounded p-3 text-xs space-y-2 relative">
                  <div className="flex justify-between items-start">
                    <div className="flex flex-col">
                      <span className="font-bold text-zinc-800">{sig.suspect_label || "Suspect Match"}</span>
                      <span className="text-[10px] text-zinc-400 font-mono">Loc: {sig.location_name}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono ${
                      sig.match_category === "CONFIRMED" ? "bg-emerald-100 text-emerald-800" :
                      sig.match_category === "PROBABLE" ? "bg-blue-100 text-blue-800" :
                      "bg-amber-100 text-amber-800"
                    }`}>
                      {sig.confidence_score.toFixed(0)}%
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-[10px] pt-1.5 border-t border-zinc-200/40">
                    <span className="text-zinc-400 font-mono">{new Date(sig.captured_at).toLocaleTimeString("en-IN")}</span>
                    
                    {sig.is_verified ? (
                      <span className="text-emerald-600 font-mono flex items-center gap-1">
                        <CheckCircle className="w-3.5 h-3.5" /> Verified
                      </span>
                    ) : (
                      <button
                        onClick={() => handleSightingVerify(sig.id)}
                        className="px-2 py-1 bg-white border border-zinc-200 hover:border-zinc-400 rounded text-[9px] font-medium text-zinc-700 transition-colors cursor-pointer"
                      >
                        Verify Sighting
                      </button>
                    )}
                  </div>
                </div>
              ))}

              {loadingSightings && sightings.length === 0 && (
                <div className="text-center py-6 text-zinc-400 text-xs">Loading sightings...</div>
              )}

              {!loadingSightings && sightings.length === 0 && (
                <div className="text-center py-6 text-zinc-400 text-xs font-mono">No face matches logged.</div>
              )}
            </div>
          </div>

          {/* Section: Cameras List & Add camera */}
          <div className="bg-white/80 backdrop-blur-sm border border-zinc-200 rounded-md p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <h2 className="text-sm font-bold text-zinc-800 flex items-center gap-2">
                <Camera className="w-4 h-4 text-zinc-500" />
                CCTV Camera Registry
              </h2>
              <button
                onClick={() => setShowCamForm(!showCamForm)}
                className="p-1.5 border border-zinc-200 bg-white hover:bg-zinc-50 rounded shadow-sm text-zinc-600 cursor-pointer"
                title="Register Camera"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Camera Creation Form */}
            {showCamForm && (
              <form onSubmit={handleCameraRegister} className="bg-zinc-50 border border-zinc-200 rounded p-4 space-y-3">
                <h3 className="text-xs font-bold text-zinc-700 uppercase tracking-wider font-mono">
                  Register CCTV Node
                </h3>

                {formError && (
                  <div className="text-[10px] text-red-600 bg-red-50 p-2 border border-red-100 rounded font-mono">
                    {formError}
                  </div>
                )}

                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Camera ID</label>
                  <input
                    type="text"
                    value={cameraId}
                    onChange={(e) => setCameraId(e.target.value)}
                    placeholder="e.g. ONG-CAM-05"
                    className="w-full bg-white border border-zinc-200 rounded px-2 py-1 text-xs text-zinc-700"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Location Name</label>
                  <input
                    type="text"
                    value={locationName}
                    onChange={(e) => setLocationName(e.target.value)}
                    placeholder="e.g. Ongole Railway Station Entry"
                    className="w-full bg-white border border-zinc-200 rounded px-2 py-1 text-xs text-zinc-700"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Latitude</label>
                    <input
                      type="number"
                      step="any"
                      value={latitude}
                      onChange={(e) => setLatitude(e.target.value)}
                      placeholder="e.g. 15.505"
                      className="w-full bg-white border border-zinc-200 rounded px-2 py-1 text-xs text-zinc-700"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Longitude</label>
                    <input
                      type="number"
                      step="any"
                      value={longitude}
                      onChange={(e) => setLongitude(e.target.value)}
                      placeholder="e.g. 80.049"
                      className="w-full bg-white border border-zinc-200 rounded px-2 py-1 text-xs text-zinc-700"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">RTSP URL</label>
                  <input
                    type="text"
                    value={rtspUrl}
                    onChange={(e) => setRtspUrl(e.target.value)}
                    placeholder="rtsp://admin:pass@ip:554/stream"
                    className="w-full bg-white border border-zinc-200 rounded px-2 py-1 text-xs text-zinc-700 font-mono"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-1.5">
                  <button
                    type="button"
                    onClick={() => setShowCamForm(false)}
                    className="px-3 py-1.5 bg-white border border-zinc-200 hover:bg-zinc-50 text-zinc-700 rounded text-xs transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={registering}
                    className="px-3 py-1.5 bg-zinc-950 text-white hover:bg-zinc-800 rounded text-xs font-bold transition-colors cursor-pointer"
                  >
                    {registering ? "Saving..." : "Save Camera"}
                  </button>
                </div>
              </form>
            )}

            {/* Cameras Status List */}
            <div className="space-y-2.5 max-h-[300px] overflow-y-auto">
              {cameras.map((c) => (
                <div key={c.id} className="bg-zinc-50/80 border border-zinc-200 rounded p-2.5 text-xs flex justify-between items-center">
                  <div className="flex flex-col gap-0.5">
                    <strong className="text-zinc-800 font-mono">{c.camera_id}</strong>
                    <span className="text-[10px] text-zinc-500">{c.location_name}</span>
                    <span className="text-[9px] text-zinc-400 font-mono flex items-center gap-1 mt-0.5">
                      <MapPin className="w-2.5 h-2.5 shrink-0" />
                      {c.latitude.toFixed(4)}, {c.longitude.toFixed(4)}
                    </span>
                  </div>

                  <button
                    disabled={updatingCameraId === c.id}
                    onClick={() => handleCameraStatusToggle(c.camera_id, c.status)}
                    className={`px-2 py-1 text-[9px] font-bold font-mono border rounded shadow-sm transition-colors cursor-pointer ${
                      c.status === "ONLINE"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                        : c.status === "MAINTENANCE"
                        ? "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100"
                        : "bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100"
                    }`}
                  >
                    {updatingCameraId === c.id ? "..." : c.status}
                  </button>
                </div>
              ))}

              {loadingCameras && cameras.length === 0 && (
                <div className="text-center py-6 text-zinc-400 text-xs">Loading cameras...</div>
              )}

              {!loadingCameras && cameras.length === 0 && (
                <div className="text-center py-6 text-zinc-400 text-xs font-mono">No registered cameras.</div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
