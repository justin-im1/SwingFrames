"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { CompareView } from "@/components/compare/CompareView";
import { api } from "@/lib/api";
import type { SwingOut } from "@/types/api";
import { getStoredSessionId } from "@/lib/client";

function CompareInner() {
  const params = useSearchParams();
  const a = params.get("a");
  const b = params.get("b");
  const [swingA, setSwingA] = useState<SwingOut | null>(null);
  const [swingB, setSwingB] = useState<SwingOut | null>(null);
  const [swings, setSwings] = useState<SwingOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pickA, setPickA] = useState(a ?? "");
  const [pickB, setPickB] = useState(b ?? "");

  useEffect(() => {
    void (async () => {
      try {
        const sid = getStoredSessionId();
        if (sid) {
          const session = await api.getSession(sid);
          setSwings(session.swings.filter((s) => s.transcode_status === "ready"));
        }
        if (a) setSwingA(await api.getSwing(a));
        if (b) setSwingB(await api.getSwing(b));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load compare.");
      }
    })();
  }, [a, b]);

  async function loadPair() {
    if (!pickA || !pickB) return;
    setSwingA(await api.getSwing(pickA));
    setSwingB(await api.getSwing(pickB));
  }

  if (error) {
    return (
      <p className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
        {error}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-mute">Compare</p>
        <h1 className="display text-3xl">Side by side</h1>
      </div>
      <div className="flex flex-wrap gap-3">
        <select
          className="rounded-lg border border-line bg-panel px-3 py-2 text-sm"
          value={pickA}
          onChange={(e) => setPickA(e.target.value)}
        >
          <option value="">Swing A</option>
          {swings.map((s, i) => (
            <option key={s.id} value={s.id}>
              {i + 1}. {s.filename ?? s.id.slice(0, 8)}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-line bg-panel px-3 py-2 text-sm"
          value={pickB}
          onChange={(e) => setPickB(e.target.value)}
        >
          <option value="">Swing B</option>
          {swings.map((s, i) => (
            <option key={s.id} value={s.id}>
              {i + 1}. {s.filename ?? s.id.slice(0, 8)}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="rounded-lg bg-lime px-3 py-2 text-sm text-ink"
          onClick={() => void loadPair()}
        >
          Load
        </button>
      </div>
      {swingA?.transcode_status === "ready" &&
        swingB?.transcode_status === "ready" && (
          <CompareView swingA={swingA} swingB={swingB} />
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
