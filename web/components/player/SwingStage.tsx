"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { formatAngle } from "@/lib/format";
import type {
  AimOut,
  AnnotationKind,
  AnnotationOut,
  CalibrationOut,
  CameraView,
  LineSeg,
  OutcomeResult,
  Point,
  SwingOut,
} from "@/types/api";
import { AnnotationCanvas } from "@/components/canvas/AnnotationCanvas";
import { Scrubber } from "@/components/player/Scrubber";
import { VideoPlayer, clampFrame } from "@/components/player/VideoPlayer";
import { OUTCOMES } from "@/lib/format";

type Tool = AnnotationKind | "measure" | "heel" | "none";

const TOOLS: { id: Tool; label: string }[] = [
  { id: "none", label: "Scrub" },
  { id: "line", label: "Line" },
  { id: "angle", label: "Angle" },
  { id: "circle", label: "Circle" },
  { id: "freehand", label: "Path" },
  { id: "measure", label: "Measure" },
];

function twoPointCameraAngle(a: Point, b: Point): { deg: number; vs: string } {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const vsVert = (Math.atan2(dx, -dy) * 180) / Math.PI;
  const vsHorz = (Math.atan2(-dy, dx) * 180) / Math.PI;
  if (Math.abs(vsVert) <= Math.abs(vsHorz)) {
    return { deg: vsVert, vs: "vertical" };
  }
  return { deg: vsHorz, vs: "horizontal" };
}

function threePointAngle(a: Point, b: Point, c: Point): number {
  const v1x = a.x - b.x;
  const v1y = a.y - b.y;
  const v2x = c.x - b.x;
  const v2y = c.y - b.y;
  const n1 = Math.hypot(v1x, v1y);
  const n2 = Math.hypot(v2x, v2y);
  const cos = Math.max(-1, Math.min(1, (v1x * v2x + v1y * v2y) / (n1 * n2)));
  return (Math.acos(cos) * 180) / Math.PI;
}

export function SwingStage({ swing }: { swing: SwingOut }) {
  const fps = swing.fps ?? 30;
  const frameCount = swing.frame_count ?? 1;
  const [frame, setFrame] = useState(0);
  const [seek, setSeek] = useState({ frame: 0, token: 0 });
  const [tool, setTool] = useState<Tool>("none");
  const [draft, setDraft] = useState<Point[]>([]);
  const [items, setItems] = useState<AnnotationOut[]>([]);
  const [undo, setUndo] = useState<AnnotationOut[]>([]);
  const [redo, setRedo] = useState<AnnotationOut[]>([]);
  const [measureNote, setMeasureNote] = useState<string | null>(null);
  const [stickyNext, setStickyNext] = useState(false);
  const [view, setView] = useState<CameraView>("face_on");
  const [sep, setSep] = useState("0.40");
  const [len, setLen] = useState("1.22");
  const [calib, setCalib] = useState<CalibrationOut | null>(null);
  const [aim, setAim] = useState<AimOut | null>(null);
  const [outcome, setOutcome] = useState<OutcomeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const go = useCallback(
    (next: number) => {
      const f = clampFrame(next, frameCount);
      setFrame(f);
      setSeek((s) => ({ frame: f, token: s.token + 1 }));
    },
    [frameCount]
  );

  useEffect(() => {
    void (async () => {
      const [anns, cal, am, oc] = await Promise.all([
        api.listAnnotations(swing.id),
        api.getCalibration(swing.id),
        api.getAim(swing.id),
        api.getOutcome(swing.id),
      ]);
      setItems(anns);
      setCalib(cal);
      setAim(am);
      setOutcome(oc?.result ?? null);
    })();
  }, [swing.id]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.key === "ArrowLeft" || e.key === "ArrowRight" || e.key === " ") {
        return;
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        e.preventDefault();
        if (e.shiftKey) void redoLast();
        else void undoLast();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [frame, go, items, undo, redo]);

  async function persist(kind: AnnotationKind, points: Point[]) {
    const created = await api.createAnnotation(swing.id, {
      frame,
      kind,
      points,
      sticky: stickyNext,
    });
    setItems((prev) => [...prev, created]);
    setUndo((prev) => [...prev, created]);
    setRedo([]);
    if (tool === "measure") {
      if (points.length === 2) {
        const a = twoPointCameraAngle(points[0], points[1]);
        setMeasureNote(
          `${a.deg >= 0 ? "+" : ""}${a.deg.toFixed(1)}° from ${a.vs} (camera-relative)`
        );
      } else if (points.length >= 3) {
        setMeasureNote(
          `${threePointAngle(points[0], points[1], points[2]).toFixed(1)}° at vertex (camera-relative)`
        );
      }
    }
  }

  async function undoLast() {
    const last = undo[undo.length - 1];
    if (!last) return;
    await api.deleteAnnotation(last.id);
    setItems((prev) => prev.filter((a) => a.id !== last.id));
    setUndo((prev) => prev.slice(0, -1));
    setRedo((prev) => [...prev, last]);
  }

  async function redoLast() {
    const last = redo[redo.length - 1];
    if (!last) return;
    const created = await api.createAnnotation(swing.id, {
      frame: last.frame,
      kind: last.kind,
      points: last.points,
      sticky: last.sticky,
      label: last.label,
      style: last.style,
    });
    setItems((prev) => [...prev, created]);
    setUndo((prev) => [...prev, created]);
    setRedo((prev) => prev.slice(0, -1));
  }

  async function onComplete(kind: AnnotationKind, points: Point[]) {
    if (tool === "heel") {
      setBusy(true);
      setError(null);
      try {
        const result = await api.measureAim(swing.id, {
          method: "heel_taps",
          heel_a: points[0],
          heel_b: points[1],
        });
        setAim(result);
        setTool("none");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Aim failed.");
      } finally {
        setBusy(false);
      }
      return;
    }
    await persist(kind, points);
  }

  async function runCalibrate() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.calibrate(swing.id, {
        frame,
        view,
        stick_length_m: Number(len) || 1.22,
        stick_separation_m: Number(sep) || 0.4,
      });
      setCalib(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Calibration failed.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmToeAim() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.measureAim(swing.id, { method: "toe_stick" });
      setAim(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Aim failed.");
    } finally {
      setBusy(false);
    }
  }

  const overlay = useMemo(() => {
    const lines: { kind: "line"; a: Point; b: Point; label?: string }[] = [];
    if (calib) {
      for (const ln of calib.calib_lines) {
        lines.push({ kind: "line", a: ln.a, b: ln.b, label: "target" });
      }
      if (calib.toe_line) {
        lines.push({
          kind: "line",
          a: calib.toe_line.a,
          b: calib.toe_line.b,
          label: "toes",
        });
      }
    }
    return lines;
  }, [calib]);

  const w = swing.width ?? 16;
  const h = swing.height ?? 9;

  return (
    <div className="space-y-4">
      <div className="flex justify-center">
        <div
          className="relative overflow-hidden rounded-2xl border border-line bg-black"
          style={{
            width: `min(40rem, 100%, calc(26rem * ${w} / ${h}))`,
            aspectRatio: `${w} / ${h}`,
          }}
        >
          <VideoPlayer
            src={api.mediaUrl(swing.id)}
            fps={fps}
            frameCount={frameCount}
            seekFrame={seek.frame}
            seekToken={seek.token}
            onPresentedFrame={setFrame}
            className="absolute inset-0 h-full w-full object-contain"
          />
          <AnnotationCanvas
            annotations={items}
            frame={frame}
            intrinsicW={w}
            intrinsicH={h}
            tool={tool}
            draft={draft}
            onDraft={setDraft}
            onComplete={onComplete}
            overlay={overlay}
          />
        </div>
      </div>
      <Scrubber
        frame={frame}
        frameCount={frameCount}
        fps={swing.fps}
        onSeek={go}
        onStep={(d) => go(frame + d)}
        listenKeys
      />
      <div className="flex flex-wrap gap-2">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => {
              setTool(t.id);
              setDraft([]);
            }}
            className={`rounded-full border px-3 py-1 text-sm ${
              tool === t.id
                ? "border-lime bg-lime/15 text-lime"
                : "border-line text-mute hover:text-chalk"
            }`}
          >
            {t.label}
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2 text-sm text-mute">
          <input
            type="checkbox"
            checked={stickyNext}
            onChange={(e) => setStickyNext(e.target.checked)}
          />
          Sticky
        </label>
        <button type="button" className="text-sm text-mute hover:text-chalk" onClick={() => void undoLast()}>
          Undo
        </button>
        <button type="button" className="text-sm text-mute hover:text-chalk" onClick={() => void redoLast()}>
          Redo
        </button>
      </div>
      {measureNote && (
        <p className="rounded-lg border border-line bg-panel px-3 py-2 text-sm text-chalk">
          {measureNote}
        </p>
      )}
      {tool === "measure" && (
        <p className="text-xs text-mute">
          Two taps: angle vs vertical/horizontal. Three taps: angle at the vertex.
          These are camera-relative — valid for comparing swings from the same camera, not
          against someone else&apos;s numbers.
        </p>
      )}

      <section className="grid gap-4 rounded-2xl border border-line bg-panel p-4 lg:grid-cols-2">
        <div>
          <h3 className="text-sm uppercase tracking-[0.16em] text-mute">Aim</h3>
          <p className="mt-1 text-sm text-mute">
            Two parallel sticks define the target line. A third across the toes is
            the accurate measurement. No distant target tap.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <select
              className="rounded-lg border border-line bg-ink px-2 py-1 text-sm"
              value={view}
              onChange={(e) => setView(e.target.value as CameraView)}
            >
              <option value="face_on">Face-on</option>
              <option value="down_the_line">Down the line</option>
            </select>
            <label className="text-sm text-mute">
              L m
              <input
                className="ml-1 w-16 rounded border border-line bg-ink px-1 py-0.5"
                value={len}
                onChange={(e) => setLen(e.target.value)}
              />
            </label>
            <label className="text-sm text-mute">
              Sep m
              <input
                className="ml-1 w-16 rounded border border-line bg-ink px-1 py-0.5"
                value={sep}
                onChange={(e) => setSep(e.target.value)}
              />
            </label>
            <button
              type="button"
              disabled={busy}
              onClick={() => void runCalibrate()}
              className="rounded-lg bg-lime px-3 py-1 text-sm text-ink disabled:opacity-50"
            >
              Detect sticks
            </button>
          </div>
          {calib && (
            <div className="mt-3 space-y-2 text-sm">
              <p>
                Residual {calib.residual_px.toFixed(2)} px · {calib.line_count} lines
                {calib.message ? ` · ${calib.message}` : ""}
              </p>
              {calib.toe_line ? (
                <button
                  type="button"
                  className="rounded-lg border border-lime/40 px-3 py-1 text-lime"
                  onClick={() => void confirmToeAim()}
                >
                  Measure toe-stick aim
                </button>
              ) : view === "face_on" ? (
                <button
                  type="button"
                  className="rounded-lg border border-line px-3 py-1"
                  onClick={() => {
                    setTool("heel");
                    setDraft([]);
                  }}
                >
                  Tap heels (face-on fallback, wider error band)
                </button>
              ) : (
                <p className="text-warn">
                  Down-the-line with two sticks cannot report a number. Add a toe
                  stick.
                </p>
              )}
            </div>
          )}
          {aim && (
            <p className="mt-3 text-lg text-chalk">
              {aim.feet_angle_deg != null
                ? formatAngle(aim.feet_angle_deg, aim.error_band_deg)
                : aim.verdict?.replace("_", " ")}
              <span className="ml-2 text-xs uppercase text-mute">{aim.method}</span>
            </p>
          )}
          {aim?.message && <p className="text-sm text-warn">{aim.message}</p>}
        </div>
        <div>
          <h3 className="text-sm uppercase tracking-[0.16em] text-mute">Ball flight</h3>
          <p className="mt-1 text-sm text-mute">
            What you saw. Tagged as an observation, not a diagnosis.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {OUTCOMES.map((o) => (
              <button
                key={o}
                type="button"
                onClick={() => {
                  setOutcome(o);
                  void api.tagOutcome(swing.id, o);
                }}
                className={`rounded-full border px-3 py-1 text-sm ${
                  outcome === o
                    ? "border-lime bg-lime/15 text-lime"
                    : "border-line text-mute hover:text-chalk"
                }`}
              >
                {o}
              </button>
            ))}
          </div>
        </div>
      </section>
      {error && (
        <p className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
          {error}
        </p>
      )}
    </div>
  );
}
