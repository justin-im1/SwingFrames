export function viewLabel(view: string): string {
  if (view === "down_the_line") return "Down the line";
  if (view === "face_on") return "Face-on";
  return view;
}

export function formatFrame(n: number, fps: number | null): string {
  if (fps && fps > 0) {
    return `${n}  ·  ${(n / fps).toFixed(3)}s`;
  }
  return String(n);
}

export function formatAngle(deg: number | null, band?: number | null): string {
  if (deg == null || !Number.isFinite(deg)) return "—";
  const dir = deg > 0 ? "R" : deg < 0 ? "L" : "";
  const core = `${deg >= 0 ? "+" : ""}${deg.toFixed(1)}°`;
  if (band != null) return `${core} ${dir}  ±${band.toFixed(1)}°`;
  return `${core} ${dir}`.trim();
}

export const OUTCOMES = [
  "straight",
  "slice",
  "hook",
  "pull",
  "push",
  "thin",
  "fat",
  "topped",
] as const;
