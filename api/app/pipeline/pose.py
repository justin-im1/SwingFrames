"""MediaPipe Pose extraction using world landmarks (metric 3D)."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from app.pipeline.landmarks import N_LANDMARKS

_BLANK = np.full((N_LANDMARKS, 3), np.nan)
_BLANK_VIS = np.zeros(N_LANDMARKS)


def extract_pose(
    frames: Iterable[np.ndarray],
    model_complexity: int = 2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run MediaPipe Pose on BGR frames.

    Returns
    -------
    xyz : (N, 33, 3)
        pose_world_landmarks in meters, origin at hip center.
    vis : (N, 33)
        Per-landmark visibility in [0, 1].
    image_lm : (N, 33, 3)
        Normalized 2D image landmarks — used only for view classification,
        never for angular metrics.
    """
    import cv2
    import mediapipe as mp

    xyz_rows: list[np.ndarray] = []
    vis_rows: list[np.ndarray] = []
    img_rows: list[np.ndarray] = []

    with mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=model_complexity,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb)
            if result.pose_world_landmarks:
                wlm = result.pose_world_landmarks.landmark
                xyz_rows.append(
                    np.array([[lm.x, lm.y, lm.z] for lm in wlm], dtype=float)
                )
                vis_rows.append(np.array([lm.visibility for lm in wlm], dtype=float))
            else:
                xyz_rows.append(_BLANK.copy())
                vis_rows.append(_BLANK_VIS.copy())
            if result.pose_landmarks:
                ilm = result.pose_landmarks.landmark
                img_rows.append(
                    np.array([[lm.x, lm.y, lm.z] for lm in ilm], dtype=float)
                )
            else:
                img_rows.append(_BLANK.copy())

    if not xyz_rows:
        raise ValueError("No frames were processed.")
    return (
        np.stack(xyz_rows, axis=0),
        np.stack(vis_rows, axis=0),
        np.stack(img_rows, axis=0),
    )
