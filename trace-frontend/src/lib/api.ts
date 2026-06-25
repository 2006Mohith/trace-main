import {
  mockCases,
  mockSuspectsByCase,
  mockNetworkByCase,
  mockEventsByCase,
  mockSharedContactsByCase,
  mockSuspectProfiles,
  mockMovementBySuspect,
  mockHeatmapBySuspect,
  mockGlobalHandlers,
} from "./mockData";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Global mock state check
let useMock = false;

// Initialize in-memory tables for mock mode mutations
const memoryCases = [...mockCases];
const memorySuspectsByCase = { ...mockSuspectsByCase };
const memoryNetworkByCase = { ...mockNetworkByCase };
const memoryEventsByCase = { ...mockEventsByCase };
const memorySharedContactsByCase = { ...mockSharedContactsByCase };
const memorySuspectProfiles = { ...mockSuspectProfiles };
const memoryMovementBySuspect = { ...mockMovementBySuspect };
const memoryHeatmapBySuspect = { ...mockHeatmapBySuspect };
const memoryGlobalHandlers = [...mockGlobalHandlers];

// Simple base64 PDF of a minimal valid PDF page:
// Displays: "TRACE - Criminal Intelligence Platform" and "Demo Mode - PDF Report Simulation"
const dummyPdfBase64 = "data:application/pdf;base64,JVBERi0xLjQKMSAwIG9iagogIDw8IC9UeXBlIC9DYXRhbG9nCiAgICAgL1BhZ2VzIDIgMCBSCiAgPj4KZW5kb2JqCjIgMCBvYmoKICA8PCAvVHlwZSAvUGFnZXMKICAgICAvS2lkcyBbIDMgMCBSIF0KICAgICAvQ291bnQgMQogID4+CmVuZG9iagozIDAgb2JqCiAgPDwgL1R5cGUgL1BhZ2UKICAgICAvUGFyZW50IDIgMCBSCiAgICAgL01lZGlhQm94IFsgMCAwIDU5NSA4NDIgXQogICAgIC9Db250ZW50cyA0IDAgUgogICAgIC9SZXNvdXJjZXMgPDwgL0ZvbnQgPDwgL0YxIDUgMCBSID4+ID4+CiAgPj4KZW5kb2JqCjQgMCBvYmoKICA8PCAvTGVuZ3RoIDcwID4+CnN0cmVhbQpCVAovRjEgMjQgVGYKNzAgNzIwIFRkCihUUkFDRSAtIENyaW1pbmFsIEludGVsbGlnZW5jZSBQbGF0Zm9ybSkgVGoKMCAtMzAgVGQKKERlbW8gTW9kZSAtIFBERiBSZXBvcnQgU2ltdWxhdGlvbikgVGoKRVQKZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqCiAgPDwgL1R5cGUgL0ZvbnQKICAgICAvU3VidHlwZSAvVHlwZTEKICAgICAvQmFzZUZvbnQgL0hlbHZldGljYQogID4+CmVuZG9iagp4cmVmCjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA1OCAwMDAwMCBuIAowMDAwMDAwMTE1IDAwMDAwIGYgCjAwMDAwMDAyNDQgMDAwMDAgbiAKMDAwMDAwMDM2NSAwMDAwMCBuIAp0cmFpbGVyCiAgPDwgL1NpemUgNgogICAgIC9Sb290IDEgMCBSCiAgPj4Kc3RhcnR4cmVmCjQ1NQolJUVPRgo=";

// Helper to parse query parameters from a path string
function parseQuery(path: string): Record<string, string> {
  const qIdx = path.indexOf("?");
  if (qIdx === -1) return {};
  const qs = path.substring(qIdx + 1);
  const params: Record<string, string> = {};
  qs.split("&").forEach((part) => {
    const [k, v] = part.split("=");
    if (k) params[decodeURIComponent(k)] = decodeURIComponent(v || "");
  });
  return params;
}

// In-memory mock API requests dispatcher
function handleMockRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const cleanPath = path.split("?")[0];
  const query = parseQuery(path);

  // 1. GET /cases
  if (cleanPath === "/cases" && (!options || options.method === "GET" || !options.method)) {
    return Promise.resolve(memoryCases as unknown as T);
  }

  // 2. POST /cases
  if (cleanPath === "/cases" && options?.method === "POST") {
    const body = JSON.parse(options.body as string);
    const caseId = "case-" + Math.random().toString(36).substring(2, 11);
    const newCase = {
      id: caseId,
      name: body.name,
      created_at: new Date().toISOString(),
      suspect_count: 0,
      event_count: 0,
    };
    memoryCases.unshift(newCase);
    memorySuspectsByCase[caseId] = [];
    memoryNetworkByCase[caseId] = { nodes: [], edges: [] };
    memoryEventsByCase[caseId] = [];
    memorySharedContactsByCase[caseId] = [];
    return Promise.resolve(newCase as unknown as T);
  }

  // 3. GET /cases/{id}
  if (cleanPath.startsWith("/cases/") && cleanPath.split("/").length === 3 && (!options || options.method === "GET" || !options.method)) {
    const id = cleanPath.split("/")[2];
    const c = memoryCases.find((x) => x.id === id);
    if (!c) return Promise.reject(new Error("Case not found"));
    return Promise.resolve(c as unknown as T);
  }

  // 4. GET /cases/{id}/suspects
  if (cleanPath.startsWith("/cases/") && cleanPath.endsWith("/suspects") && (!options || options.method === "GET" || !options.method)) {
    const id = cleanPath.split("/")[2];
    return Promise.resolve((memorySuspectsByCase[id] || []) as unknown as T);
  }

  // 5. GET /cases/{id}/network
  if (cleanPath.startsWith("/cases/") && cleanPath.endsWith("/network") && (!options || options.method === "GET" || !options.method)) {
    const id = cleanPath.split("/")[2];
    return Promise.resolve((memoryNetworkByCase[id] || { nodes: [], edges: [] }) as unknown as T);
  }

  // 6. GET /cases/{id}/events
  if (cleanPath.startsWith("/cases/") && cleanPath.endsWith("/events") && (!options || options.method === "GET" || !options.method)) {
    const id = cleanPath.split("/")[2];
    let evs = memoryEventsByCase[id] || [];
    if (query.event_type) {
      evs = evs.filter((e) => e.event_type === query.event_type);
    }
    if (query.severity) {
      evs = evs.filter((e) => e.severity === query.severity);
    }
    return Promise.resolve(evs as unknown as T);
  }

  // 7. POST /cases/{id}/analyze
  if (cleanPath.startsWith("/cases/") && cleanPath.endsWith("/analyze") && options?.method === "POST") {
    const id = cleanPath.split("/")[2];
    const evs = memoryEventsByCase[id] || [];
    const count = evs.length;
    return Promise.resolve({
      events_generated: count,
      summary: {
        ANOMALY: evs.filter((e) => e.event_type === "ANOMALY").length,
        CO_LOCATION: evs.filter((e) => e.event_type === "CO_LOCATION").length,
        IMEI_SWAP: evs.filter((e) => e.event_type === "IMEI_SWAP").length,
        COMMON_CONTACT: evs.filter((e) => e.event_type === "COMMON_CONTACT").length,
      },
    } as unknown as T);
  }

  // 8. GET /cases/{id}/shared-contacts
  if (cleanPath.startsWith("/cases/") && cleanPath.endsWith("/shared-contacts") && (!options || options.method === "GET" || !options.method)) {
    const id = cleanPath.split("/")[2];
    return Promise.resolve((memorySharedContactsByCase[id] || []) as unknown as T);
  }

  // 9. GET /suspects/{id}/profile
  if (cleanPath.startsWith("/suspects/") && cleanPath.endsWith("/profile") && (!options || options.method === "GET" || !options.method)) {
    const id = cleanPath.split("/")[2];
    const profile = memorySuspectProfiles[id];
    if (!profile) return Promise.reject(new Error("Suspect not found"));
    return Promise.resolve(profile as unknown as T);
  }

  // 10. GET /suspects/{id}/movement
  if (cleanPath.startsWith("/suspects/") && cleanPath.endsWith("/movement") && (!options || options.method === "GET" || !options.method)) {
    const id = cleanPath.split("/")[2];
    return Promise.resolve((memoryMovementBySuspect[id] || []) as unknown as T);
  }

  // 11. GET /suspects/{id}/call_heatmap
  if (cleanPath.startsWith("/suspects/") && cleanPath.endsWith("/call_heatmap") && (!options || options.method === "GET" || !options.method)) {
    const id = cleanPath.split("/")[2];
    return Promise.resolve((memoryHeatmapBySuspect[id] || []) as unknown as T);
  }

  // 12. GET /global/handler-numbers
  if (cleanPath === "/global/handler-numbers" && (!options || options.method === "GET" || !options.method)) {
    return Promise.resolve(memoryGlobalHandlers as unknown as T);
  }

  return Promise.reject(new Error(`Endpoint not mock-supported: ${cleanPath}`));
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  if (useMock) {
    return handleMockRequest<T>(path, options);
  }
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...options?.headers },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  } catch (e: any) {
    if (
      e.message?.includes("Failed to fetch") ||
      e.message?.includes("Load failed") ||
      e.message?.includes("NetworkError") ||
      e.message?.includes("Failed to connect")
    ) {
      console.warn("TRACE Backend not detected on localhost:8000. Activating offline Demo Mode.");
      useMock = true;
      return handleMockRequest<T>(path, options);
    }
    throw e;
  }
}

export const api = {
  // Cases
  getCases: () => request<import("./types").CaseOut[]>("/cases"),
  createCase: (name: string) =>
    request<import("./types").CaseOut>("/cases", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  getCase: (id: string) => request<import("./types").CaseOut>(`/cases/${id}`),
  deleteCase: async (id: string) => {
    if (useMock) {
      const idx = memoryCases.findIndex((x) => x.id === id);
      if (idx !== -1) memoryCases.splice(idx, 1);
      delete memorySuspectsByCase[id];
      delete memoryNetworkByCase[id];
      delete memoryEventsByCase[id];
      delete memorySharedContactsByCase[id];
      return Promise.resolve();
    }
    try {
      const res = await fetch(`${API_BASE}/cases/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
    } catch (e: any) {
      if (e.message?.includes("Failed to fetch") || e.message?.includes("NetworkError")) {
        useMock = true;
        const idx = memoryCases.findIndex((x) => x.id === id);
        if (idx !== -1) memoryCases.splice(idx, 1);
        return Promise.resolve();
      }
      throw e;
    }
  },

  // Upload
  uploadRecords: async (
    caseId: string,
    suspectLabel: string,
    cdrFile: File,
    ipdrFile?: File
  ): Promise<import("./types").UploadResponse> => {
    if (useMock) {
      const suspectId = "mock-suspect-" + Math.random().toString(36).substring(2, 11);
      const msisdn = "9199" + Math.floor(10000000 + Math.random() * 90000000);
      const newSuspect = {
        id: suspectId,
        case_id: caseId,
        label: suspectLabel,
        primary_msisdn: msisdn,
        anomaly_score: Math.random() * 40 + 35,
        event_count: 3,
      };

      if (!memorySuspectsByCase[caseId]) {
        memorySuspectsByCase[caseId] = [];
      }
      memorySuspectsByCase[caseId].push(newSuspect);

      // Update case stats
      const c = memoryCases.find((x) => x.id === caseId);
      if (c) {
        c.suspect_count = (c.suspect_count || 0) + 1;
        c.event_count = (c.event_count || 0) + 3;
      }

      // Initialize profiles
      memorySuspectProfiles[suspectId] = {
        suspect: newSuspect,
        cdr_summary: {
          total_calls: 38,
          total_sms: 12,
          unique_contacts: 8,
          avg_duration_sec: 132.5,
          night_call_ratio: 0.15,
          burst_score: 2.1,
          anomaly_score: newSuspect.anomaly_score,
        },
        ipdr_summary: {
          total_sessions: 64,
          total_data_kb: 32050.4,
          ott_breakdown: [
            { app: "WhatsApp", session_count: 40, total_data_kb: 21000.2, first_seen: new Date().toISOString(), last_seen: new Date().toISOString() },
            { app: "Signal", session_count: 24, total_data_kb: 11050.2, first_seen: new Date().toISOString(), last_seen: new Date().toISOString() },
          ],
        },
        events: [
          { id: suspectId + "-ev1", case_id: caseId, event_type: "ANOMALY", severity: "HIGH", involved_suspects: [suspectLabel], detail: { anomaly_score: newSuspect.anomaly_score }, occurred_at: new Date().toISOString() },
          { id: suspectId + "-ev2", case_id: caseId, event_type: "IMEI_SWAP", severity: "HIGH", involved_suspects: [suspectLabel], detail: { old_imei: "860124039485712", new_imei: "860124039485999" }, occurred_at: new Date().toISOString() },
          { id: suspectId + "-ev3", case_id: caseId, event_type: "OTT_USAGE", severity: "LOW", involved_suspects: [suspectLabel], detail: { app: "Signal encrypted tunnel" }, occurred_at: new Date().toISOString() },
        ],
        call_heatmap_data: [
          { day_of_week: 1, hour_of_day: 10, call_count: 4 },
          { day_of_week: 2, hour_of_day: 15, call_count: 9 },
          { day_of_week: 4, hour_of_day: 22, call_count: 12 },
        ],
        movement_data: [
          { tower_id: "TWR-ONG-001", lat: 15.5057, lon: 80.0499, timestamp: new Date().toISOString(), co_location: false, co_location_with: [] },
          { tower_id: "TWR-ONG-002", lat: 15.5120, lon: 80.0620, timestamp: new Date().toISOString(), co_location: true, co_location_with: ["Target Handler B"] },
        ],
      };

      memoryMovementBySuspect[suspectId] = memorySuspectProfiles[suspectId].movement_data;
      memoryHeatmapBySuspect[suspectId] = memorySuspectProfiles[suspectId].call_heatmap_data;

      // Update events list
      if (!memoryEventsByCase[caseId]) memoryEventsByCase[caseId] = [];
      memoryEventsByCase[caseId].unshift(...memorySuspectProfiles[suspectId].events);

      // Update network nodes & edges
      if (!memoryNetworkByCase[caseId]) memoryNetworkByCase[caseId] = { nodes: [], edges: [] };
      memoryNetworkByCase[caseId].nodes.push({ id: suspectId, label: suspectLabel, node_type: "suspect", suspect_id: suspectId });
      if (memoryNetworkByCase[caseId].nodes.length > 1) {
        // connect to the first suspect
        const targetId = memoryNetworkByCase[caseId].nodes[0].id;
        if (targetId !== suspectId) {
          memoryNetworkByCase[caseId].edges.push({ source: suspectId, target: targetId, call_count: 5, total_duration_sec: 420 });
        }
      }

      return Promise.resolve({ suspect_id: suspectId, rows_inserted_cdr: 50, rows_inserted_ipdr: 64 });
    }

    const form = new FormData();
    form.append("suspect_label", suspectLabel);
    form.append("cdr_file", cdrFile);
    if (ipdrFile) form.append("ipdr_file", ipdrFile);
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(e.detail || `HTTP ${res.status}`);
      }
      return res.json() as Promise<import("./types").UploadResponse>;
    } catch (e: any) {
      if (e.message?.includes("Failed to fetch") || e.message?.includes("NetworkError")) {
        useMock = true;
        return api.uploadRecords(caseId, suspectLabel, cdrFile, ipdrFile);
      }
      throw e;
    }
  },

  // Analysis
  runAnalysis: (caseId: string) =>
    request<import("./types").AnalysisSummary>(`/cases/${caseId}/analyze`, {
      method: "POST",
    }),

  // Events
  getEvents: (caseId: string, eventType?: string, severity?: string) => {
    const params = new URLSearchParams();
    if (eventType) params.set("event_type", eventType);
    if (severity) params.set("severity", severity);
    const qs = params.toString() ? `?${params}` : "";
    return request<import("./types").EventOut[]>(`/cases/${caseId}/events${qs}`);
  },

  // Network
  getNetwork: (caseId: string) =>
    request<import("./types").NetworkGraphOut>(`/cases/${caseId}/network`),

  // Suspects
  getSuspects: (caseId: string) =>
    request<import("./types").SuspectOut[]>(`/cases/${caseId}/suspects`),

  getSuspectProfile: (suspectId: string) =>
    request<import("./types").SuspectProfileOut>(`/suspects/${suspectId}/profile`),

  getMovement: (suspectId: string) =>
    request<import("./types").MovementPoint[]>(`/suspects/${suspectId}/movement`),

  getCallHeatmap: (suspectId: string) =>
    request<import("./types").CallHeatmapRow[]>(`/suspects/${suspectId}/call_heatmap`),

  deleteSuspect: async (id: string): Promise<void> => {
    if (useMock) {
      // Find case ID
      let foundCaseId = "";
      for (const [cid, list] of Object.entries(memorySuspectsByCase)) {
        const found = list.find((s) => s.id === id);
        if (found) {
          foundCaseId = cid;
          memorySuspectsByCase[cid] = list.filter((s) => s.id !== id);
          break;
        }
      }

      // Update case stats
      if (foundCaseId) {
        const c = memoryCases.find((x) => x.id === foundCaseId);
        if (c) {
          c.suspect_count = Math.max(0, (c.suspect_count || 0) - 1);
        }
        if (memoryNetworkByCase[foundCaseId]) {
          memoryNetworkByCase[foundCaseId].nodes = memoryNetworkByCase[foundCaseId].nodes.filter((n: any) => n.id !== id);
          memoryNetworkByCase[foundCaseId].edges = memoryNetworkByCase[foundCaseId].edges.filter((e: any) => e.source !== id && e.target !== id);
        }
      }

      delete memorySuspectProfiles[id];
      delete memoryMovementBySuspect[id];
      delete memoryHeatmapBySuspect[id];
      return Promise.resolve();
    }

    try {
      const res = await fetch(`${API_BASE}/suspects/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
    } catch (e: any) {
      if (e.message?.includes("Failed to fetch") || e.message?.includes("NetworkError")) {
        useMock = true;
        return api.deleteSuspect(id);
      }
      throw e;
    }
  },

  getSharedContacts: (caseId: string) =>
    request<import("./types").SharedContact[]>(`/cases/${caseId}/shared-contacts`),

  getGlobalHandlers: () =>
    request<{ number: string; case_count: number; total_calls: number }[]>("/global/handler-numbers"),

  // Geo Intel — Radial Search
  radialSearch: (
    caseId: string,
    centerLat: number,
    centerLon: number,
    radiusKm: number,
    startTime?: string,
    endTime?: string
  ) => {
    if (useMock) {
      return Promise.resolve({
        query: { center_lat: centerLat, center_lon: centerLon, radius_km: radiusKm },
        hits: [],
        suspects_found: [],
        total_hits: 0,
      });
    }
    return request<{
      query: Record<string, unknown>;
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
    }>(`/cases/${caseId}/radial-search`, {
      method: "POST",
      body: JSON.stringify({
        center_lat: centerLat,
        center_lon: centerLon,
        radius_km: radiusKm,
        start_time: startTime || null,
        end_time: endTime || null,
      }),
    });
  },

  // Audit Trail
  getAuditLogs: (limit = 100, actionType?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (actionType) params.set("action_type", actionType);
    return request<{
      total: number;
      offset: number;
      limit: number;
      logs: {
        id: string;
        action_type: string;
        entity_type: string;
        entity_id: string | null;
        entity_label: string | null;
        officer_ip: string | null;
        officer_host: string | null;
        detail: Record<string, unknown>;
        timestamp: string;
      }[];
    }>(`/audit/logs?${params.toString()}`);
  },

  // Report PDF
  getReportUrl: (suspectId: string) => {
    if (useMock) {
      return dummyPdfBase64;
    }
    return `${API_BASE}/suspects/${suspectId}/report.pdf`;
  },

  // Templates
  getCdrTemplateUrl: () => `${API_BASE}/templates/cdr`,
  getIpdrTemplateUrl: () => `${API_BASE}/templates/ipdr`,

  // CCTV Plugin Endpoints
  getCameras: () => request<any[]>("/cctv/cameras"),
  registerCamera: (payload: { camera_id: string; location_name: string; latitude: number; longitude: number; rtsp_url: string }) =>
    request<any>("/cctv/cameras", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateCameraStatus: (cameraId: string, status: string) =>
    request<any>(`/cctv/cameras/${cameraId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  registerFace: async (suspectId: string, imageFile: File) => {
    const form = new FormData();
    form.append("file", imageFile);
    const res = await fetch(`${API_BASE}/cctv/register-face/${suspectId}`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const e = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(e.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },
  deleteFace: (suspectId: string, faceId: string) =>
    request<any>(`/cctv/face/${suspectId}/${faceId}`, {
      method: "DELETE",
    }),
  matchMedia: async (file: File, sampleRate = 15) => {
    const form = new FormData();
    form.append("file", file);
    form.append("sample_rate", String(sampleRate));
    const res = await fetch(`${API_BASE}/cctv/match`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const e = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(e.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },
  getRecentSightings: (limit = 50) => request<any[]>(`/cctv/sightings/recent?limit=${limit}`),
  getSuspectSightings: (suspectId: string) => request<any[]>(`/cctv/sightings/${suspectId}`),
  verifySighting: (sightingId: string, verified: boolean, officerNote?: string) =>
    request<any>(`/cctv/sightings/${sightingId}/verify`, {
      method: "POST",
      body: JSON.stringify({ verified, officer_note: officerNote }),
    }),
  getFaceQuality: (suspectId: string) => request<any[]>(`/cctv/suspect/${suspectId}/face-quality`),
};
