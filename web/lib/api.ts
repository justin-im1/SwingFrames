import { getClientId } from "@/lib/client";
import type {
  Comparison,
  ConsistencyOut,
  ProBenchmark,
  SessionDetail,
  SessionOut,
  SwingCreateResponse,
  SwingFeatures,
  SwingMetrics,
  SwingSummary,
} from "@/types/api";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Client-Id", getClientId());
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      detail = await res.text();
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
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
  consistency: (id: string) =>
    request<ConsistencyOut>(`/api/sessions/${id}/consistency`),
  uploadSwing: (file: File, sessionId?: string, handedness?: string) => {
    const body = new FormData();
    body.append("file", file);
    if (sessionId) body.append("session_id", sessionId);
    if (handedness) body.append("handedness", handedness);
    return request<SwingCreateResponse>("/api/swings", { method: "POST", body });
  },
  getSwing: (id: string) => request<SwingSummary>(`/api/swings/${id}`),
  flagView: (id: string, note?: string) =>
    request<SwingSummary>(`/api/swings/${id}/flag-view`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note: note ?? null }),
    }),
  getMetrics: (id: string) => request<SwingMetrics>(`/api/swings/${id}/metrics`),
  getFeatures: (id: string) =>
    request<SwingFeatures>(`/api/swings/${id}/features`),
  compare: (a: string, b: string) =>
    request<Comparison>("/api/comparisons", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ swing_a_id: a, swing_b_id: b }),
    }),
  benchmarks: () => request<ProBenchmark[]>("/api/benchmarks/pros"),
};
