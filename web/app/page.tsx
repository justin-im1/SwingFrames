"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { DropZone } from "@/components/DropZone";
import { api } from "@/lib/api";
import { getStoredSessionId, setStoredSessionId } from "@/lib/client";
import { viewLabel } from "@/lib/format";
import type { SessionOut, SwingSummary } from "@/types/api";

export default function HomePage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionOut[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [swings, setSwings] = useState<SwingSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (id: string | null) => {
    const list = await api.listSessions();
    setSessions(list);
    if (!id) return;
    const detail = await api.getSession(id);
    setSwings(detail.swings);
  }, []);

  useEffect(() => {
    const existing = getStoredSessionId();
    void (async () => {
      try {
        if (!existing) {
          const created = await api.createSession();
          setStoredSessionId(created.id);
          setSessionId(created.id);
          await refresh(created.id);
        } else {
          setSessionId(existing);
          await refresh(existing);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load sessions.");
      }
    })();
  }, [refresh]);

  async function onFile(file: File) {
    if (!sessionId) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.uploadSwing(file, sessionId);
      router.push(`/swings/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setBusy(false);
    }
  }

  async function newSession() {
    const created = await api.createSession();
    setStoredSessionId(created.id);
    setSessionId(created.id);
    await refresh(created.id);
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[1.2fr_0.8fr]">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-lime-dim">
          Phone video in · timing out
        </p>
        <h1 className="display mt-2 text-4xl leading-tight sm:text-5xl">
          Measure when things happen, not where they appear.
        </h1>
        <p className="mt-4 max-w-xl text-mute">
          Camera angle wrecks joint angles. Tempo, sequence, and consistency
          mostly survive. 60 fps required; the clip is deleted after analysis.
        </p>
        <div className="mt-8">
          <DropZone onFile={onFile} busy={busy} />
        </div>
        {error && (
          <p className="mt-4 rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
            {error}
          </p>
        )}
      </div>
      <aside className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm uppercase tracking-[0.16em] text-mute">
            This session
          </h2>
          <button
            type="button"
            onClick={() => void newSession()}
            className="text-sm text-lime hover:underline"
          >
            New session
          </button>
        </div>
        {sessions.length > 1 && (
          <select
            className="w-full rounded-lg border border-line bg-panel px-3 py-2 text-sm"
            value={sessionId ?? ""}
            onChange={(e) => {
              setStoredSessionId(e.target.value);
              setSessionId(e.target.value);
              void refresh(e.target.value);
            }}
          >
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label ?? "Session"} · {s.swing_count} swings
              </option>
            ))}
          </select>
        )}
        <ul className="space-y-2">
          {swings.length === 0 && (
            <li className="rounded-xl border border-line bg-panel px-4 py-6 text-sm text-mute">
              No swings yet. Drop a clip to start.
            </li>
          )}
          {swings.map((s, i) => (
            <li key={s.id}>
              <Link
                href={`/swings/${s.id}`}
                className="flex items-center justify-between rounded-xl border border-line bg-panel px-4 py-3 hover:border-lime/50"
              >
                <span>Swing {i + 1}</span>
                <span className="text-xs text-mute">
                  {s.status}
                  {s.status === "ready" ? ` · ${viewLabel(s.view_class)}` : ""}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        {sessionId && swings.filter((s) => s.status === "ready").length >= 3 && (
          <Link
            href={`/sessions/${sessionId}`}
            className="block rounded-xl border border-lime/40 bg-lime/10 px-4 py-3 text-center text-sm text-lime"
          >
            Consistency for this session
          </Link>
        )}
      </aside>
    </div>
  );
}
