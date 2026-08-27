import type { AnnotationKind, AnnotationOut, Point } from "@/types/api";
import { toCanvas } from "@/lib/videoBox";

const COLOR = "#c6f54e";

export function visibleForFrame(items: AnnotationOut[], frame: number) {
  return items.filter((a) => a.sticky || a.frame === frame);
}

function drawLine(
  ctx: CanvasRenderingContext2D,
  a: Point,
  b: Point,
  w: number,
  h: number
) {
  const pa = toCanvas(a, { width: w, height: h });
  const pb = toCanvas(b, { width: w, height: h });
  ctx.beginPath();
  ctx.moveTo(pa.x, pa.y);
  ctx.lineTo(pb.x, pb.y);
  ctx.stroke();
}

function drawPoints(
  ctx: CanvasRenderingContext2D,
  points: Point[],
  w: number,
  h: number
) {
  for (const p of points) {
    const c = toCanvas(p, { width: w, height: h });
    ctx.beginPath();
    ctx.arc(c.x, c.y, 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

function vertexAngle(a: Point, b: Point, c: Point): number {
  const v1x = a.x - b.x;
  const v1y = a.y - b.y;
  const v2x = c.x - b.x;
  const v2y = c.y - b.y;
  const n1 = Math.hypot(v1x, v1y);
  const n2 = Math.hypot(v2x, v2y);
  if (n1 < 1e-6 || n2 < 1e-6) return 0;
  const cos = Math.max(-1, Math.min(1, (v1x * v2x + v1y * v2y) / (n1 * n2)));
  return (Math.acos(cos) * 180) / Math.PI;
}

export function drawAnnotation(
  ctx: CanvasRenderingContext2D,
  item: { kind: AnnotationKind; points: Point[]; label?: string | null },
  w: number,
  h: number
) {
  ctx.save();
  ctx.strokeStyle = COLOR;
  ctx.fillStyle = COLOR;
  ctx.lineWidth = 2;
  ctx.font = "12px ui-monospace, monospace";
  const pts = item.points;
  if (item.kind === "line" && pts.length >= 2) {
    drawLine(ctx, pts[0], pts[1], w, h);
    drawPoints(ctx, pts.slice(0, 2), w, h);
  } else if (item.kind === "angle" && pts.length >= 3) {
    drawLine(ctx, pts[0], pts[1], w, h);
    drawLine(ctx, pts[1], pts[2], w, h);
    drawPoints(ctx, pts.slice(0, 3), w, h);
    const vertex = toCanvas(pts[1], { width: w, height: h });
    const deg = vertexAngle(pts[0], pts[1], pts[2]);
    ctx.fillText(`${deg.toFixed(1)}°`, vertex.x + 8, vertex.y - 8);
  } else if (item.kind === "circle" && pts.length >= 2) {
    const c = toCanvas(pts[0], { width: w, height: h });
    const r = toCanvas(pts[1], { width: w, height: h });
    const radius = Math.hypot(r.x - c.x, r.y - c.y);
    ctx.beginPath();
    ctx.arc(c.x, c.y, radius, 0, Math.PI * 2);
    ctx.stroke();
    drawPoints(ctx, [pts[0], pts[1]], w, h);
  } else if (item.kind === "freehand" && pts.length >= 2) {
    ctx.beginPath();
    const first = toCanvas(pts[0], { width: w, height: h });
    ctx.moveTo(first.x, first.y);
    for (let i = 1; i < pts.length; i++) {
      const p = toCanvas(pts[i], { width: w, height: h });
      ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
  if (item.label) {
    const p = toCanvas(pts[0], { width: w, height: h });
    ctx.fillText(item.label, p.x + 6, p.y - 6);
  }
  ctx.restore();
}

export function neededPoints(kind: AnnotationKind): number {
  if (kind === "line" || kind === "circle") return 2;
  if (kind === "angle") return 3;
  return 0;
}
