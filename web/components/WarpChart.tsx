"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Comparison, SwingFeatures } from "@/types/api";
import { stride } from "@/lib/format";

export function WarpChart({ comparison }: { comparison: Comparison }) {
  const path = stride(
    (comparison.warping_path ?? []).map(([i, j]) => ({ i, j })),
    500
  );
  const n = path.at(-1)?.i ?? 1;
  const m = path.at(-1)?.j ?? 1;
  const diagonal = [
    { i: 0, j: 0 },
    { i: n, j: m },
  ];
  const deviation = stride(
    comparison.timing_divergence?.deviation_curve ?? [],
    500
  );

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-2xl border border-line bg-panel p-5">
        <h3 className="display text-lg">Warping path</h3>
        <p className="mb-3 text-xs text-mute">
          Off-diagonal means one swing is ahead in the motion.
        </p>
        <div className="h-72">
          <ResponsiveContainer>
            <ScatterChart>
              <CartesianGrid stroke="#2c3a33" />
              <XAxis
                dataKey="i"
                type="number"
                tick={{ fill: "#8b9a91", fontSize: 11 }}
                name="swing A"
              />
              <YAxis
                dataKey="j"
                type="number"
                tick={{ fill: "#8b9a91", fontSize: 11 }}
                name="swing B"
              />
              <Tooltip
                contentStyle={{
                  background: "#141c18",
                  border: "1px solid #2c3a33",
                }}
              />
              <Scatter data={diagonal} fill="#8b9a91" line />
              <Scatter data={path} fill="#c6f54e" line />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </section>
      <section className="rounded-2xl border border-line bg-panel p-5">
        <h3 className="display text-lg">Deviation curve</h3>
        <p className="mb-3 text-xs text-mute">
          j/m − i/n. Positive: swing B is further through the motion. Do not
          average this over a phase.
        </p>
        <div className="h-72">
          <ResponsiveContainer>
            <LineChart data={deviation}>
              <CartesianGrid stroke="#2c3a33" />
              <XAxis
                dataKey="i_rel"
                type="number"
                domain={[0, 1]}
                tick={{ fill: "#8b9a91", fontSize: 11 }}
              />
              <YAxis tick={{ fill: "#8b9a91", fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: "#141c18",
                  border: "1px solid #2c3a33",
                }}
              />
              <Line
                type="monotone"
                dataKey="deviation"
                stroke="#c6f54e"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}

export function WristOverlay({
  a,
  b,
  enabled,
  reason,
}: {
  a: SwingFeatures;
  b: SwingFeatures;
  enabled: boolean;
  reason: string | null;
}) {
  if (!enabled) {
    return (
      <section className="rounded-2xl border border-warn/40 bg-warn/10 p-5 text-sm text-warn">
        {reason ??
          "Positional overlay is disabled because the view classes do not match."}
      </section>
    );
  }
  const dataA = stride(
    (a.wrist_position ?? []).map((p, i) => ({
      x: p[0],
      y: p[1],
      t: a.timestamps[i],
    })),
    300
  ).filter((d) => d.x != null && d.y != null);
  const dataB = stride(
    (b.wrist_position ?? []).map((p, i) => ({
      x: p[0],
      y: p[1],
      t: b.timestamps[i],
    })),
    300
  ).filter((d) => d.x != null && d.y != null);

  return (
    <section className="rounded-2xl border border-line bg-panel p-5">
      <h3 className="display text-lg">Lead-wrist path</h3>
      <p className="mb-3 text-xs text-mute">
        Same view class — overlay is an illustration, not a score.
      </p>
      <div className="h-72">
        <ResponsiveContainer>
          <ScatterChart>
            <CartesianGrid stroke="#2c3a33" />
            <XAxis dataKey="x" type="number" tick={{ fill: "#8b9a91" }} />
            <YAxis dataKey="y" type="number" tick={{ fill: "#8b9a91" }} />
            <Tooltip
              contentStyle={{
                background: "#141c18",
                border: "1px solid #2c3a33",
              }}
            />
            <Scatter data={dataA} fill="#c6f54e" name="A" line />
            <Scatter data={dataB} fill="#5dcea8" name="B" line />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
