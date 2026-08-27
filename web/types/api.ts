export type TranscodeStatus = "pending" | "ready" | "failed";
export type AnnotationKind = "line" | "angle" | "circle" | "freehand";
export type CameraView = "face_on" | "down_the_line";
export type AimMethod = "toe_stick" | "heel_taps";
export type OutcomeResult =
  | "straight"
  | "slice"
  | "hook"
  | "pull"
  | "push"
  | "thin"
  | "fat"
  | "topped";
export type SyncMode = "independent" | "offset" | "normalized";

export type Point = { x: number; y: number };

export type LineSeg = {
  a: Point;
  b: Point;
  role?: "calib" | "toe" | null;
};

export type SessionOut = {
  id: string;
  user_id: string;
  created_at: string;
  label: string | null;
  swing_count: number;
};

export type SwingCreateResponse = {
  id: string;
  session_id: string;
  transcode_status: TranscodeStatus;
};

export type SwingOut = {
  id: string;
  session_id: string;
  created_at: string;
  label: string | null;
  filename: string | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  frame_count: number | null;
  duration_s: number | null;
  distinct_frame_ratio: number | null;
  transcode_status: TranscodeStatus;
  error_message: string | null;
  low_distinct_frames: boolean;
};

export type SessionDetail = SessionOut & { swings: SwingOut[] };

export type AnnotationOut = {
  id: string;
  swing_id: string;
  frame: number;
  kind: AnnotationKind;
  points: Point[];
  style: Record<string, unknown> | null;
  label: string | null;
  sticky: boolean;
  created_at: string;
};

export type CalibrationOut = {
  swing_id: string;
  frame: number;
  homography: number[][];
  stick_length_m: number;
  stick_separation_m: number;
  residual_px: number;
  view: CameraView;
  calib_lines: LineSeg[];
  toe_line: LineSeg | null;
  line_count: number;
  message: string | null;
};

export type AimOut = {
  id: string;
  swing_id: string;
  method: AimMethod;
  view: CameraView;
  heel_a: Point | null;
  heel_b: Point | null;
  toe_line: LineSeg | null;
  feet_angle_deg: number | null;
  error_band_deg: number | null;
  verdict: string | null;
  message: string | null;
  created_at: string;
};

export type OutcomeOut = {
  id: string;
  swing_id: string;
  result: OutcomeResult;
  note: string | null;
  created_at: string;
};

export type InsightsOut = {
  session_id: string;
  tagged_n: number;
  ready: boolean;
  message: string;
  lines: { text: string; n: number; outcome: OutcomeResult | null }[];
};

export type ComparisonOut = {
  id: string;
  swing_a_id: string;
  swing_b_id: string;
  sync_mode: SyncMode;
  anchor_a: number | null;
  anchor_b: number | null;
  created_at: string;
};
