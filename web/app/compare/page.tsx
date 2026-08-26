"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { WarpChart, WristOverlay } from "@/components/WarpChart";
import { api } from "@/lib/api";
import type { Comparison, SwingFeatures } from "@/types/api";

function CompareInner() {
  const params = useSearchParams();
  const a = params.get("a");
  const b = params.get("b");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [fa, setFa] = useState<SwingFeatures | null>(null);
  const [fb, setFb] = useState<SwingFeatures | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!a || !b) return;
    setLoading(true);
    void (async () => {
      try {
        const [c, featA, featB] = await Promise.all([
          api.compare(a, b),
          api.getFeatures(a),
          api.getFeatures(b),
        ]);
        setComparison(c);
        setFa(featA);
        setFb(featB);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Compare failed.");
      } finally {
        setLoading(false);
      }
    })();
  }, [a, b]);

  if (!a || !b) {
    return (
      <p className="text-mute">
        Pick two swings from a session page, or add <code>?a=&amp;b=</code> IDs
        to this URL.
      </p>
    );
  }
  if (error) return <p className="text-bad">{error}</p>;
  if (loading || !comparison) return <p className="text-mute">Aligning…</p>;

  const ratios = comparison.timing_divergence?.phase_duration_ratios ?? [];

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-mute">
          DTW · normalized distance{" "}
          {comparison.dtw_normalized_distance?.toFixed(3) ?? "—"}
        </p>
        <h1 className="display text-3xl">Two-swing comparison</h1>
      </div>
      <ul className="grid gap-3 sm:grid-cols-3">
        {ratios.map((r) => (
          <li
            key={r.name}
            className="rounded-2xl border border-line bg-panel p-4"
          >
            <p className="text-xs uppercase tracking-[0.14em] text-mute">
              {r.name.replace("_", " ")}
            </p>
            <p className="mt-2 text-sm">{r.message}</p>
            <p className="mt-2 text-xs text-mute">
              {r.swing_a_s?.toFixed(2)}s → {r.swing_b_s?.toFixed(2)}s
            </p>
          </li>
        ))}
      </ul>
      <WarpChart comparison={comparison} />
      {fa && fb && (
        <WristOverlay
          a={fa}
          b={fb}
          enabled={comparison.positional_comparable}
          reason={comparison.disabled_reason}
        />
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<p className="text-mute">Loading…</p>}>
      <CompareInner />
    </Suspense>
  );
}
