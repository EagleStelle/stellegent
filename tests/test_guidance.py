import numpy as np
import cv2
from stellegent.capture.guidance import (
    analyze_frame, perspective_skew_deg, horizontal_offset_ratio,
)


def test_analyze_no_board():
    img = np.full((720, 1280, 3), 200, dtype=np.uint8)
    res = analyze_frame(img)
    assert res.corners is None
    assert any("Board" in m or "blurry" in m for m in res.messages)


def test_skew_zero_for_rectangle():
    corners = np.array([[0, 0], [100, 0], [100, 50], [0, 50]], dtype=np.float32)
    assert perspective_skew_deg(corners) < 1.0


def test_offset_centered():
    corners = np.array([[400, 100], [880, 100], [880, 600], [400, 600]],
                       dtype=np.float32)
    assert abs(horizontal_offset_ratio(corners, 1280)) < 0.01
