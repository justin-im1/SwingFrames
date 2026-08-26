import type { QualityFlag } from "@/types/api";

const tone: Record<QualityFlag["severity"], string> = {
  info: "border-line text-mute",
  warning: "border-warn/40 bg-warn/10 text-warn",
  error: "border-bad/40 bg-bad/10 text-bad",
};

export function QualityFlags({ flags }: { flags: QualityFlag[] }) {
  if (!flags.length) return null;
  return (
    <div className="space-y-2">
      <h3 className="text-xs uppercase tracking-[0.16em] text-mute">
        Quality flags
      </h3>
      <ul className="space-y-2">
        {flags.map((flag, i) => (
          <li
            key={`${flag.code}-${i}`}
            className={`rounded-lg border px-3 py-2 text-sm ${tone[flag.severity]}`}
          >
            <span className="font-medium">{flag.code}</span>
            <span className="mx-2 text-mute">·</span>
            {flag.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
