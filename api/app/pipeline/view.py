"""View classification from 2D image landmarks (apparent shoulder width)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.pipeline.landmarks import (
    LEFT_HIP,
    LEFT_SHOULDER,
    RIGHT_HIP,
    RIGHT_SHOULDER,
)

# Apparent shoulder-separation / torso-height at address (image space).
# Calibrated on synthetic projections; tune on labelled footage.
FACE_ON_MIN = 0.70
DTL_MAX = 0.45
CONFIDENCE_FLOOR = 0.45


@dataclass
class ViewResult:
    view_class: str
    confidence: float
    ratio: float
    quality_flags: list[dict]


def shoulder_torso_ratio(image_lm: np.ndarray, address_idx: int) -> float:
    frame = image_lm[address_idx]
    ls = frame[LEFT_SHOULDER, :2]
    rs = frame[RIGHT_SHOULDER, :2]
    lh = frame[LEFT_HIP, :2]
    rh = frame[RIGHT_HIP, :2]
    if not np.all(np.isfinite([*ls, *rs, *lh, *rh])):
        return float("nan")
    shoulder_sep = float(np.linalg.norm(ls - rs))
    torso_h = float(np.linalg.norm((ls + rs) / 2.0 - (lh + rh) / 2.0))
    if torso_h < 1e-6:
        return float("nan")
    return shoulder_sep / torso_h


def classify_view(image_lm: np.ndarray, address_idx: int) -> ViewResult:
    """Classify camera view. Never trust a user-supplied label for gating."""
    flags: list[dict] = []
    ratio = shoulder_torso_ratio(image_lm, address_idx)
    if not np.isfinite(ratio):
        return ViewResult(
            view_class="unknown",
            confidence=0.0,
            ratio=ratio,
            quality_flags=[
                {
                    "code": "view_unknown",
                    "severity": "warning",
                    "message": "Could not measure apparent shoulder width; positional comparison disabled.",
                    "details": {},
                }
            ],
        )

    if ratio >= FACE_ON_MIN:
        view_class = "face_on"
        # How far past the threshold, scaled into ~[0.5, 1].
        confidence = float(np.clip(0.5 + (ratio - FACE_ON_MIN) / 0.6, 0.0, 1.0))
    elif ratio <= DTL_MAX:
        view_class = "down_the_line"
        confidence = float(np.clip(0.5 + (DTL_MAX - ratio) / 0.35, 0.0, 1.0))
    else:
        view_class = "unknown"
        mid = 0.5 * (FACE_ON_MIN + DTL_MAX)
        span = 0.5 * (FACE_ON_MIN - DTL_MAX)
        confidence = float(np.clip(1.0 - abs(ratio - mid) / max(span, 1e-6), 0.0, 0.49))

    if confidence < CONFIDENCE_FLOOR:
        view_class = "unknown"
        flags.append(
            {
                "code": "view_low_confidence",
                "severity": "warning",
                "message": (
                    f"View classification confidence {confidence:.2f} is below "
                    f"{CONFIDENCE_FLOOR:.2f}; positional comparison disabled."
                ),
                "details": {"ratio": ratio, "confidence": confidence},
            }
        )
    elif view_class == "unknown":
        flags.append(
            {
                "code": "view_unknown",
                "severity": "warning",
                "message": (
                    f"Apparent shoulder/torso ratio {ratio:.2f} is between view classes. "
                    "Positional comparison disabled."
                ),
                "details": {"ratio": ratio, "confidence": confidence},
            }
        )

    return ViewResult(
        view_class=view_class,
        confidence=confidence,
        ratio=ratio,
        quality_flags=flags,
    )
