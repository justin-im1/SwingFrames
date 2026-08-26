"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { QualityFlags } from "@/components/QualityFlags";
import { SequenceChart } from "@/components/SequenceChart";
import { SkeletonView } from "@/components/SkeletonView";
import { TempoCard } from "@/components/TempoCard";
import { api } from "@/lib/api";
import { viewLabel } from "@/lib/format";
import type {
  ProBenchmark,
  SwingFeatures,
  SwingMetrics,
  SwingSummary,
} from "@/types/api";

export default function SwingPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [swing, setSwing] = useState<SwingSummary | null>(null);
  const [metrics, setMetrics] = useState<SwingMetrics | null>(null);
  const [features, setFeatures] = useState<SwingFeatures | null>(null);
  const [benchmarks, setBenchmarks] = useState<ProBenchmark[]>([]);
  const [benchId, setBenchId] = useState("tour_average");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    void api.benchmarks().then((b) => {
      if (!stop) setBenchmarks(b);
    });
    const poll = async () => {
      try {
        const s = await api.getSwing(id);
        if (stop) return;
        setSwing(s);
        if (s.status === "ready") {
          const [m, f] = await Promise.all([
            api.getMetrics(id),
            api.getFeatures(id),
          ]);
          if (stop) return;
          setMetrics(m);
          setFeatures(f);
          return;
        }
        if (s.status === "failed") return;
        window.setTimeout(() => void poll(), 1000);
      } catch (err) {
        if (!stop)
          setError(err instanceof Error ? err.message : "Failed to load swing.");
      }
    };
    void poll();
    return () => {
      stop = true;
    };
  }, [id]);

  if (error) {
    return <p className="text-bad">{error}</p>;
  }
  if (!swing) {
    return <p className="text-mute">Loading…</p>;
  }

  const processing = swing.status === "uploaded" || swing.status === "processing";
  const bench = benchmarks.find((b) => b.id === benchId) ?? benchmarks[0] ?? null;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-mute">
            {swing.status}
            {swing.source_fps ? ` · ${swing.source_fps.toFixed(0)} fps` : ""}
          </p>
          <h1 className="display text-3xl">Single swing</h1>
        </div>
        <Link href={`/sessions/${swing.session_id}`} className="text-sm text-lime">
          Session →
        </Link>
      </div>

      {processing && (
        <p className="rounded-xl border border-line bg-panel px-4 py-6 text-mute">
          Extracting pose and running the pipeline. A 10s 240 fps clip is thousands
          of MediaPipe frames — this is why we don&apos;t block the upload request.
        </p>
      )}

      {swing.status === "failed" && (
        <p className="rounded-xl border border-bad/40 bg-bad/10 px-4 py-4 text-bad">
          {swing.error_message ?? "Analysis failed. The video was discarded."}
        </p>
      )}

      {swing.status === "ready" && (
        <>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="rounded-full border border-line px-3 py-1">
              {viewLabel(swing.view_class)}
              {swing.view_confidence != null
                ? ` · ${Math.round(swing.view_confidence * 100)}%`
                : ""}
            </span>
            {!swing.is_usable && (
              <span className="rounded-full border border-warn/40 px-3 py-1 text-warn">
                Low confidence — treat numbers as suspect
              </span>
            )}
            {!swing.view_flagged_wrong && (
              <button
                type="button"
                className="text-mute underline-offset-2 hover:text-chalk hover:underline"
                onClick={() => void api.flagView(id).then(setSwing)}
              >
                Flag view as wrong
              </button>
            )}
            {swing.view_flagged_wrong && (
              <span className="text-mute">View flagged (not overridden)</span>
            )}
          </div>

          {metrics && (
            <TempoCard
              metrics={metrics}
              benchmark={bench}
              benchmarks={benchmarks}
              onBenchmark={setBenchId}
            />
          )}
          {metrics && features && (
            <SequenceChart features={features} metrics={metrics} />
          )}
          <QualityFlags flags={swing.quality_flags} />
          {features && (
            <section className="rounded-2xl border border-line bg-panel p-5">
              <h2 className="display mb-3 text-xl">Skeleton overlay</h2>
              <SkeletonView features={features} />
            </section>
          )}
        </>
      )}
    </div>
  );
}
