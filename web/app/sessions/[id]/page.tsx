"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { metricLabel, viewLabel } from "@/lib/format";
import type { ConsistencyOut, SessionDetail } from "@/types/api";

export default function SessionPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [consistency, setConsistency] = useState<ConsistencyOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pick, setPick] = useState<string[]>([]);

  useEffect(() => {
    void (async () => {
      try {
        const [s, c] = await Promise.all([
          api.getSession(id),
          api.consistency(id),
        ]);
        setSession(s);
        setConsistency(c);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load session.");
      }
    })();
  }, [id]);

  if (error) return <p className="text-bad">{error}</p>;
  if (!session) return <p className="text-mute">Loading…</p>;

  function toggle(swingId: string) {
    setPick((prev) => {
      if (prev.includes(swingId)) return prev.filter((x) => x !== swingId);
      if (prev.length >= 2) return [prev[1], swingId];
      return [...prev, swingId];
    });
  }

  const ready = session.swings.filter((s) => s.status === "ready");

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-mute">
          {session.label} · share this URL
        </p>
        <h1 className="display text-3xl">Session consistency</h1>
        <p className="mt-2 max-w-2xl text-sm text-mute">
          Same-session pose error is systematic and cancels in the variance.
          Needs at least 3 usable swings; 5 is better. Clearing cookies loses
          this history — there are no accounts.
        </p>
      </div>

      <ul className="grid gap-2 sm:grid-cols-2">
        {session.swings.map((s, i) => (
          <li key={s.id} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={pick.includes(s.id)}
              onChange={() => toggle(s.id)}
              disabled={s.status !== "ready"}
              className="accent-lime"
            />
            <Link
              href={`/swings/${s.id}`}
              className="flex flex-1 items-center justify-between rounded-xl border border-line bg-panel px-4 py-3 text-sm hover:border-lime/40"
            >
              <span>Swing {i + 1}</span>
              <span className="text-mute">
                {s.status}
                {s.status === "ready" ? ` · ${viewLabel(s.view_class)}` : ""}
              </span>
            </Link>
          </li>
        ))}
      </ul>

      {pick.length === 2 && (
        <Link
          href={`/compare?a=${pick[0]}&b=${pick[1]}`}
          className="inline-block rounded-xl bg-lime px-4 py-2 text-sm font-medium text-ink"
        >
          Compare selected
        </Link>
      )}

      {consistency && (
        <section className="rounded-2xl border border-line bg-panel p-5">
          <h2 className="display text-xl">Repeatability</h2>
          <p className="mt-1 text-sm text-mute">{consistency.message}</p>
          {consistency.ready && (
            <>
              {consistency.least_repeatable && (
                <p className="mt-3 text-sm">
                  Least repeatable:{" "}
                  <span className="text-lime">
                    {metricLabel(consistency.least_repeatable)}
                  </span>
                </p>
              )}
              <ul className="mt-4 space-y-3">
                {consistency.metrics.map((m) => (
                  <li key={m.name}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span>{metricLabel(m.name)}</span>
                      <span className="text-mute">
                        CV {m.cv == null ? "—" : m.cv.toFixed(3)} · n={m.n}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-panel-2">
                      <div
                        className="h-full bg-lime"
                        style={{
                          width: `${Math.min(100, (m.cv ?? 0) * 200)}%`,
                        }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
      {ready.length < 3 && (
        <p className="text-sm text-mute">
          Upload more clips in this session to unlock a coefficient of variation.
        </p>
      )}
    </div>
  );
}
