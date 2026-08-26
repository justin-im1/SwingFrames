export type ViewClass = "down_the_line" | "face_on" | "unknown";
export type SwingStatus = "uploaded" | "processing" | "ready" | "failed";
export type Handedness = "right" | "left";

export type QualityFlag = {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  details?: Record<string, unknown>;
};

export type SwingCreateResponse = {
  id: string;
  status: SwingStatus;
  session_id: string;
};

export type SwingSummary = {
  id: string;
  session_id: string;
  created_at: string;
  status: SwingStatus;
  source_fps: number | null;
  frame_count: number | null;
  duration_s: number | null;
  view_class: ViewClass;
  view_confidence: number | null;
  quality_flags: QualityFlag[];
  is_usable: boolean;
  error_message: string | null;
  handedness: Handedness;
  view_flagged_wrong: boolean;
};

export type PhaseBoundary = {
  address_idx: number | null;
  top_idx: number | null;
  impact_idx: number | null;
  finish_idx: number | null;
  segmentation_confidence: number | null;
};

export type SwingMetrics = {
  swing_id: string;
  backswing_duration_s: number | null;
  downswing_duration_s: number | null;
  tempo_ratio: number | null;
  pelvis_peak_time_s: number | null;
  torso_peak_time_s: number | null;
  arm_peak_time_s: number | null;
  sequence_order_correct: boolean | null;
  pelvis_torso_gap_ms: number | null;
  torso_arm_gap_ms: number | null;
  peak_magnitude_ratios: Record<string, number> | null;
  unreliable_metrics: string[];
  phases: PhaseBoundary | null;
};

export type SwingFeatures = {
  swing_id: string;
  timestamps: number[];
  pelvis_rotation: Array<number | null> | null;
  torso_rotation: Array<number | null> | null;
  lead_arm_angle: Array<number | null> | null;
  pelvis_velocity: Array<number | null> | null;
  torso_velocity: Array<number | null> | null;
  arm_velocity: Array<number | null> | null;
  wrist_position: Array<Array<number | null>> | null;
  head_position: Array<Array<number | null>> | null;
  mean_visibility: Array<number | null> | null;
  debug_skeleton: {
    timestamps: number[];
    landmarks: number[][][];
  } | null;
};

export type PhaseDurationRatio = {
  name: string;
  swing_a_s: number | null;
  swing_b_s: number | null;
  ratio: number | null;
  percent_longer_b: number | null;
  message: string;
};

export type Comparison = {
  id: string;
  swing_a_id: string;
  swing_b_id: string;
  created_at: string;
  dtw_distance: number | null;
  dtw_normalized_distance: number | null;
  warping_path: number[][] | null;
  timing_divergence: {
    deviation_curve: Array<{
      i: number;
      j: number;
      i_rel: number;
      j_rel: number;
      deviation: number;
    }>;
    phase_duration_ratios: PhaseDurationRatio[];
  } | null;
  positional_comparable: boolean;
  disabled_reason: string | null;
};

export type SessionOut = {
  id: string;
  user_id: string;
  created_at: string;
  label: string | null;
  swing_count: number;
};

export type SessionDetail = SessionOut & { swings: SwingSummary[] };

export type ConsistencyMetric = {
  name: string;
  mean: number | null;
  std: number | null;
  cv: number | null;
  n: number;
  values: Array<number | null>;
};

export type ConsistencyOut = {
  session_id: string;
  n: number;
  usable_n: number;
  ready: boolean;
  message: string;
  metrics: ConsistencyMetric[];
  least_repeatable: string | null;
};

export type ProBenchmark = {
  id: string;
  name: string;
  tempo_ratio: number;
  backswing_s: number;
  downswing_s: number;
  source: string;
};
