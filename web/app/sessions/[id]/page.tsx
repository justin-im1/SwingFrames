"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { InsightsOut, SessionDetail } from "@/types/api";

export default function SessionPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [insights, setInsights] = useState<InsightsOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [d, i] = await Promise.all([api.getSession(id), api.insights(id)]);
        setDetail(d);
        setInsights(i);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load session.");
      }
    })();
  }, [id]);

  if (error) {
    return (
      <p className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
        {error}
      </p>
    );
  }
  if (!detail) return <p className="text-mute">Loading…</p>;

  const ready = detail.swings.filter((s) => s.transcode_status === "ready");

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-mute">Session</p>
        <h1 className="display text-3xl">{detail.label ?? "Untitled"}</h1>
        <p className="mt-2 text-sm text-mute">
          Share this URL — anyone with the link can watch. Writes still need your
          browser cookie.
        </p>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2">
        {detail.swings.map((s, i) => (
          <li key={s.id}>
            <Link
              href={`/swings/${s.id}`}
              className="flex items-center justify-between rounded-xl border border-line bg-panel px-4 py-3 hover:border-lime/50"
            >
              <span>Swing {i + 1}</span>
              <span className="text-xs text-mute">{s.transcode_status}</span>
            </Link>
          </li>
        ))}
      </ul>
      {ready.length >= 2 && (
        <Link
          href={`/compare?a=${ready[0].id}&b=${ready[1].id}`}
          className="inline-block rounded-xl border border-lime/40 bg-lime/10 px-4 py-2 text-sm text-lime"
        >
          Compare last two ready swings
        </Link>
      )}
      {insights && (
        <section className="rounded-2xl border border-line bg-panel p-5">
          <h2 className="text-sm uppercase tracking-[0.16em] text-mute">
            Correlations
          </h2>
          <p className="mt-2 text-sm text-mute">{insights.message}</p>
          <ul className="mt-4 space-y-2">
            {insights.lines.map((line, i) => (
              <li key={i} className="text-chalk">
                {line.text}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
