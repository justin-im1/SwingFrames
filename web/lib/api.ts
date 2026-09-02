import { getClientId } from "@/lib/client";
import type {
  AnnotationOut,
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
import type { AnnotationKind, Point } from "@/types/api";

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

function mediaOrigin(): string {
  if (typeof window === "undefined") return "";
  const { protocol, hostname, port } = window.location;
  // Next's /api rewrite holds HTTP/1.1 connections for Range video and
  // starves JSON fetches on the same origin — the swing page then sits on
  // "Loading…" forever. Hit FastAPI directly for media in local Next.
  if (port === "3000" || port === "3001") {
    return `${protocol}//${hostname}:8000`;
  }
  return "";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Client-Id", getClientId());
  const upload = init.body instanceof FormData;
  const timeoutMs = upload ? 10 * 60 * 1000 : 20_000;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  init.signal?.addEventListener("abort", () => ctrl.abort());
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers, signal: ctrl.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("The API did not respond. Try refreshing.");
    }
    throw new Error("Could not reach the API. Is FastAPI running on port 8000?");
  } finally {
    clearTimeout(timer);
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
  mediaUrl: (id: string) => `${mediaOrigin()}/api/media/${id}`,
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
  clearAnnotations: (swingId: string) =>
    request<void>(`/api/swings/${swingId}/annotations`, { method: "DELETE" }),
  copyAnnotations: (
    targetId: string,
    sourceId: string,
    targetFrame: number
  ) =>
    request<AnnotationOut[]>(`/api/swings/${targetId}/annotations/copy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_id: sourceId, target_frame: targetFrame }),
    }),
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
