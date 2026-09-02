"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { SwingStage } from "@/components/player/SwingStage";
import { api } from "@/lib/api";
import type { SwingOut } from "@/types/api";

export default function SwingPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [swing, setSwing] = useState<SwingOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    let timer: number | undefined;
    async function poll() {
      try {
        const data = await api.getSwing(id);
        if (cancelled) return;
        setSwing(data);
        setError(null);
        if (data.transcode_status === "pending") {
          timer = window.setTimeout(poll, 800);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load swing.");
        }
      }
    }
    void poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [id]);

  if (error) {
    return (
      <p className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
        {error}
      </p>
    );
  }
  if (!swing) {
    return <p className="text-mute">Loading…</p>;
  }
  if (swing.transcode_status === "pending") {
    return (
      <div className="rounded-2xl border border-line bg-panel px-6 py-12 text-center">
        <p className="display text-2xl">Transcoding</p>
        <p className="mt-2 text-sm text-mute">
          H.264, rotation baked in, dense keyframes. This is what makes
          frame-accurate scrubbing possible.
        </p>
      </div>
    );
  }
  if (swing.transcode_status === "failed") {
    return (
      <div className="rounded-2xl border border-bad/40 bg-bad/10 px-6 py-8">
        <p className="text-bad">Transcode failed</p>
        <p className="mt-2 text-sm text-mute">{swing.error_message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-mute">
            {swing.filename ?? "Swing"}
          </p>
          <h1 className="display text-3xl">Frame {swing.frame_count}</h1>
        </div>
        <Link href={`/sessions/${swing.session_id}`} className="text-sm text-lime">
          Session
        </Link>
      </div>
      <SwingStage swing={swing} />
    </div>
  );
}
