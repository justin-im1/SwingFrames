"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SwingFeatures, SwingMetrics } from "@/types/api";
import { formatMs, stride } from "@/lib/format";

export function SequenceChart({
  features,
  metrics,
}: {
  features: SwingFeatures;
  metrics: SwingMetrics;
}) {
  const ts = features.timestamps;
  const rows = stride(
    ts.map((t, i) => ({
      t,
      pelvis: features.pelvis_velocity?.[i] ?? null,
      torso: features.torso_velocity?.[i] ?? null,
      arm: features.arm_velocity?.[i] ?? null,
    }))
  );

  const phases = metrics.phases;
  const marks = [
    { key: "address", idx: phases?.address_idx },
    { key: "top", idx: phases?.top_idx },
    { key: "impact", idx: phases?.impact_idx },
    { key: "finish", idx: phases?.finish_idx },
  ].filter((m): m is { key: string; idx: number } => m.idx != null);

  const peaks = [
    { name: "pelvis", t: metrics.pelvis_peak_time_s, color: "#c6f54e" },
    { name: "torso", t: metrics.torso_peak_time_s, color: "#5dcea8" },
    { name: "arm", t: metrics.arm_peak_time_s, color: "#e8b84a" },
  ].filter((p) => p.t != null);

  return (
    <section className="rounded-2xl border border-line bg-panel p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="display text-xl">Kinematic sequence</h2>
        <p className="text-sm text-mute">
          {metrics.sequence_order_correct == null
            ? "Order unknown"
            : metrics.sequence_order_correct
              ? "Pelvis → torso → arms"
              : "Peak order is not pelvis → torso → arms"}
        </p>
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#2c3a33" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              type="number"
              tick={{ fill: "#8b9a91", fontSize: 11 }}
              tickFormatter={(v) => `${Number(v).toFixed(1)}s`}
            />
            <YAxis tick={{ fill: "#8b9a91", fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: "#141c18",
                border: "1px solid #2c3a33",
              }}
            />
            {marks.map((m) => (
              <ReferenceLine
                key={m.key}
                x={ts[m.idx]}
                stroke="#8b9a91"
                strokeDasharray="4 4"
                label={{
                  value: m.key,
                  fill: "#8b9a91",
                  fontSize: 10,
                  position: "top",
                }}
              />
            ))}
            <Line
              type="monotone"
              dataKey="pelvis"
              stroke="#c6f54e"
              dot={false}
              strokeWidth={2}
              name="pelvis"
            />
            <Line
              type="monotone"
              dataKey="torso"
              stroke="#5dcea8"
              dot={false}
              strokeWidth={2}
              name="torso"
            />
            <Line
              type="monotone"
              dataKey="arm"
              stroke="#e8b84a"
              dot={false}
              strokeWidth={2}
              name="arm"
            />
            {peaks.map((p) => {
              const row = rows.reduce((best, r) =>
                Math.abs(r.t - (p.t as number)) <
                Math.abs(best.t - (p.t as number))
                  ? r
                  : best
              );
              const y =
                p.name === "pelvis"
                  ? row.pelvis
                  : p.name === "torso"
                    ? row.torso
                    : row.arm;
              if (y == null) return null;
              return (
                <ReferenceDot
                  key={p.name}
                  x={row.t}
                  y={y}
                  r={5}
                  fill={p.color}
                  stroke="#0c110f"
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-mute">Pelvis–torso gap</dt>
          <dd>{formatMs(metrics.pelvis_torso_gap_ms)}</dd>
        </div>
        <div>
          <dt className="text-mute">Torso–arm gap</dt>
          <dd>{formatMs(metrics.torso_arm_gap_ms)}</dd>
        </div>
        {metrics.unreliable_metrics.length > 0 && (
          <div className="col-span-2 text-warn">
            Unreliable: {metrics.unreliable_metrics.join(", ")}
          </div>
        )}
      </dl>
    </section>
  );
}
