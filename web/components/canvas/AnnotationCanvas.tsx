"use client";

import { useCallback, useEffect, useRef } from "react";
import type { AnnotationKind, AnnotationOut, Point } from "@/types/api";
import { displayedVideoBox, toNormalized, type Box } from "@/lib/videoBox";
import { drawAnnotation, neededPoints, visibleForFrame } from "@/components/canvas/draw";

type Tool = AnnotationKind | "none";

type Props = {
  annotations: AnnotationOut[];
  frame: number;
  intrinsicW: number;
  intrinsicH: number;
  tool: Tool;
  draft: Point[];
  onDraft: (points: Point[]) => void;
  onComplete: (points: Point[]) => void;
  className?: string;
};

export function AnnotationCanvas({
  annotations,
  frame,
  intrinsicW,
  intrinsicH,
  tool,
  draft,
  onDraft,
  onComplete,
  className,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const boxRef = useRef<Box | null>(null);

  const paint = useCallback(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;
    const rect = wrap.getBoundingClientRect();
    const box = displayedVideoBox(rect, intrinsicW, intrinsicH);
    boxRef.current = box;
    const dpr = window.devicePixelRatio || 1;
    canvas.style.left = `${box.left - rect.left}px`;
    canvas.style.top = `${box.top - rect.top}px`;
    canvas.style.width = `${box.width}px`;
    canvas.style.height = `${box.height}px`;
    canvas.width = Math.max(1, Math.round(box.width * dpr));
    canvas.height = Math.max(1, Math.round(box.height * dpr));
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, box.width, box.height);
    for (const item of visibleForFrame(annotations, frame)) {
      drawAnnotation(ctx, item, box.width, box.height);
    }
    if (draft.length) {
      const kind: AnnotationKind = tool === "none" ? "line" : tool;
      drawAnnotation(
        ctx,
        { kind: kind === "freehand" && draft.length < 2 ? "line" : kind, points: draft },
        box.width,
        box.height
      );
    }
  }, [annotations, frame, intrinsicW, intrinsicH, draft, tool]);

  useEffect(() => {
    paint();
    const wrap = wrapRef.current;
    if (!wrap) return;
    const ro = new ResizeObserver(() => paint());
    ro.observe(wrap);
    return () => ro.disconnect();
  }, [paint]);

  function pointFromEvent(e: React.PointerEvent): Point | null {
    const box = boxRef.current;
    if (!box) return null;
    const p = toNormalized(e.clientX, e.clientY, box);
    if (p.x < 0 || p.x > 1 || p.y < 0 || p.y > 1) return null;
    return p;
  }

  function onPointerDown(e: React.PointerEvent) {
    if (tool === "none") return;
    const p = pointFromEvent(e);
    if (!p) return;
    (e.target as HTMLCanvasElement).setPointerCapture(e.pointerId);
    if (tool === "freehand") {
      onDraft([p]);
      return;
    }
    const next = [...draft, p];
    const need = neededPoints(tool);
    if (need > 0 && next.length >= need) {
      onComplete(next);
      onDraft([]);
    } else {
      onDraft(next);
    }
  }

  function onPointerMove(e: React.PointerEvent) {
    if (tool !== "freehand" || e.buttons === 0) return;
    const p = pointFromEvent(e);
    if (!p) return;
    onDraft([...draft, p]);
  }

  function onPointerUp() {
    if (tool === "freehand" && draft.length >= 2) {
      onComplete(draft);
      onDraft([]);
    }
  }

  return (
    <div ref={wrapRef} className={`pointer-events-none absolute inset-0 ${className ?? ""}`}>
      <canvas
        ref={canvasRef}
        className={`absolute ${tool === "none" ? "pointer-events-none" : "pointer-events-auto cursor-crosshair"}`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      />
    </div>
  );
}
