export function formatFrame(n: number, fps: number | null): string {
  if (fps && fps > 0) {
    return `${n}  ·  ${(n / fps).toFixed(3)}s`;
  }
  return String(n);
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
