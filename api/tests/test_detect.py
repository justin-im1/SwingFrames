from __future__ import annotations

import cv2
import numpy as np

from app.geometry.detect import detect_stick_lines


def test_detects_two_orange_sticks() -> None:
    img = np.zeros((480, 640, 3), np.uint8)
    img[:] = (40, 110, 40)
    orange = (0, 165, 255)
    cv2.line(img, (140, 440), (160, 50), orange, 10)
    cv2.line(img, (280, 440), (300, 50), orange, 10)
    lines = detect_stick_lines(img)
    assert len(lines) == 2
