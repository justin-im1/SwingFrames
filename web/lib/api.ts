import { getClientId } from "@/lib/client";
import type {
  AimOut,
  AnnotationOut,
  CalibrationOut,
  ComparisonOut,
  InsightsOut,
  OutcomeOut,
  OutcomeResult,
  SessionDetail,
  SessionOut,
  SwingCreateResponse,
  SwingOut,
  SyncMode,
} from "@/types/api";
import type { AnnotationKind, CameraView, LineSeg, Point } from "@/types/api";

type AimRequest = {
  method: "toe_stick" | "heel_taps";
  heel_a?: Point | null;
  heel_b?: Point | null;
  toe_line?: LineSeg | null;
};

function formatApiError(parsed: unknown, raw: string, fallback: string): string {
  if (parsed && typeof parsed === "object" && "detail" in parsed) {
    const detail = (parsed as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item) {
            const loc = Array.isArray((item as { loc?: unknown }).loc)
              ? (item as { loc: unknown[] }).loc.join(".")
              : "";
            const msg = String((item as { msg: unknown }).msg);
            return loc ? `${loc}: ${msg}` : msg;
          }
          return JSON.stringify(item);
        })
        .join("; ");
    }
    return JSON.stringify(detail);
  }
  return raw.trim() || fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Client-Id", getClientId());
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers });
  } catch {
    throw new Error("Could not reach the API. Is FastAPI running on port 8000?");
  }
  const raw = await res.text();
  let parsed: unknown = null;
  if (raw) {
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = null;
    }
  }
  if (!res.ok) {
    throw new Error(formatApiError(parsed, raw, res.statusText));
  }
  if (res.status === 204 || raw === "") return undefined as T;
  if (parsed === null) {
    if (raw.trim() === "null") return null as T;
    throw new Error(raw || "Empty response from API.");
  }
  return parsed as T;
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  createSession: (label?: string) =>
    request<SessionOut>("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: label ?? null }),
    }),
  listSessions: () => request<SessionOut[]>("/api/sessions"),
  getSession: (id: string) => request<SessionDetail>(`/api/sessions/${id}`),
  insights: (id: string) => request<InsightsOut>(`/api/sessions/${id}/insights`),
  uploadSwing: (file: File, sessionId?: string) => {
    const body = new FormData();
    body.append("file", file);
    if (sessionId) body.append("session_id", sessionId);
    return request<SwingCreateResponse>("/api/swings", { method: "POST", body });
  },
  getSwing: (id: string) => request<SwingOut>(`/api/swings/${id}`),
  mediaUrl: (id: string) => `/api/media/${id}`,
  listAnnotations: (id: string) =>
    request<AnnotationOut[]>(`/api/swings/${id}/annotations`),
  createAnnotation: (
    id: string,
    body: {
      frame: number;
      kind: AnnotationKind;
      points: Point[];
      sticky?: boolean;
      label?: string | null;
      style?: Record<string, unknown> | null;
    }
  ) =>
    request<AnnotationOut>(`/api/swings/${id}/annotations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  deleteAnnotation: (id: string) =>
    request<void>(`/api/annotations/${id}`, { method: "DELETE" }),
  calibrate: (
    id: string,
    body: {
      frame: number;
      view: CameraView;
      stick_length_m: number;
      stick_separation_m: number;
      lines?: LineSeg[] | null;
    }
  ) =>
    request<CalibrationOut>(`/api/swings/${id}/calibrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  getCalibration: (id: string) =>
    request<CalibrationOut | null>(`/api/swings/${id}/calibration`),
  measureAim: (id: string, body: AimRequest) =>
    request<AimOut>(`/api/swings/${id}/aim`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  getAim: (id: string) => request<AimOut | null>(`/api/swings/${id}/aim`),
  tagOutcome: (id: string, result: OutcomeResult, note?: string) =>
    request<OutcomeOut>(`/api/swings/${id}/outcome`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ result, note: note ?? null }),
    }),
  getOutcome: (id: string) => request<OutcomeOut | null>(`/api/swings/${id}/outcome`),
  createComparison: (
    a: string,
    b: string,
    sync_mode: SyncMode = "independent",
    anchor_a?: number | null,
    anchor_b?: number | null
  ) =>
    request<ComparisonOut>("/api/comparisons", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        swing_a_id: a,
        swing_b_id: b,
        sync_mode,
        anchor_a: anchor_a ?? null,
        anchor_b: anchor_b ?? null,
      }),
    }),
};
