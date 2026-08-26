export function viewLabel(view: string): string {
  if (view === "down_the_line") return "Down the line";
  if (view === "face_on") return "Face-on";
  return "Unknown view";
}

export function formatTempo(ratio: number | null): string {
  if (ratio == null || !Number.isFinite(ratio)) return "—";
  return `${ratio.toFixed(2)} : 1`;
}

export function formatMs(ms: number | null): string {
  if (ms == null || !Number.isFinite(ms)) return "—";
  return `${ms.toFixed(0)} ms`;
}

export function formatSec(s: number | null): string {
  if (s == null || !Number.isFinite(s)) return "—";
  return `${s.toFixed(2)} s`;
}

export function metricLabel(name: string): string {
  return name.replaceAll("_", " ");
}

export function stride<T>(items: T[], max = 400): T[] {
  if (items.length <= max) return items;
  const step = Math.ceil(items.length / max);
  return items.filter((_, i) => i % step === 0);
}
