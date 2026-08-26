"use client";

import type { ProBenchmark, SwingMetrics } from "@/types/api";
import { formatSec, formatTempo } from "@/lib/format";

export function TempoCard({
  metrics,
  benchmark,
  onBenchmark,
  benchmarks,
}: {
  metrics: SwingMetrics;
  benchmark: ProBenchmark | null;
  benchmarks: ProBenchmark[];
  onBenchmark: (id: string) => void;
}) {
  const ratio = metrics.tempo_ratio;
  const delta =
    ratio != null && benchmark ? ratio - benchmark.tempo_ratio : null;
  const unreliable = metrics.unreliable_metrics.includes("tempo_ratio");

  return (
    <section className="rounded-2xl border border-line bg-panel p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-mute">
            Tempo ratio
          </p>
          <p className="display mt-1 text-4xl text-chalk">
            {unreliable ? "unreliable" : formatTempo(ratio)}
          </p>
        </div>
        <select
          className="rounded-lg border border-line bg-panel-2 px-3 py-2 text-sm"
          value={benchmark?.id ?? ""}
          onChange={(e) => onBenchmark(e.target.value)}
        >
          {benchmarks.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name} ({b.tempo_ratio.toFixed(1)}:1)
            </option>
          ))}
        </select>
      </div>
      {unreliable ? (
        <p className="mt-3 text-sm text-warn">
          Tempo was not computed over gated-out landmarks.
        </p>
      ) : (
        <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
          <div>
            <dt className="text-mute">Backswing</dt>
            <dd>{formatSec(metrics.backswing_duration_s)}</dd>
          </div>
          <div>
            <dt className="text-mute">Downswing</dt>
            <dd>{formatSec(metrics.downswing_duration_s)}</dd>
          </div>
          <div>
            <dt className="text-mute">vs {benchmark?.name ?? "benchmark"}</dt>
            <dd>
              {delta == null
                ? "—"
                : `${delta >= 0 ? "+" : ""}${delta.toFixed(2)}`}
            </dd>
          </div>
        </dl>
      )}
      {benchmark && (
        <p className="mt-3 text-xs text-mute">{benchmark.source}</p>
      )}
    </section>
  );
}
