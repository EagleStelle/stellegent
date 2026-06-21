"""Real-time framing guidance for whiteboard capture."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import cv2
import numpy as np

from ..config import BOARD_PHYSICAL_MM, CAPTURE_DISTANCE_RANGE_M, SHARPNESS_MIN
from ..preprocess.pipeline import detect_board_corners, laplacian_sharpness


@dataclass
class GuidanceResult:
    corners: Optional[np.ndarray]
    messages: List[str] = field(default_factory=list)
    sharpness: float = 0.0
    distance_m: Optional[float] = None
    skew_deg: Optional[float] = None
    coverage: Optional[float] = None
    ready: bool = False


def _focal_px_estimate(img_w: int, hfov_deg: float = 66.0) -> float:
    return img_w / (2.0 * math.tan(math.radians(hfov_deg) / 2.0))


def estimate_distance_m(corners: np.ndarray, img_w: int) -> float:
    """solvePnP-style estimate using known board width."""
    f = _focal_px_estimate(img_w)
    top_w = np.linalg.norm(corners[1] - corners[0])
    bot_w = np.linalg.norm(corners[2] - corners[3])
    px_w = (top_w + bot_w) / 2.0
    if px_w <= 1:
        return float("inf")
    board_mm_w = BOARD_PHYSICAL_MM[0]
    return (f * board_mm_w) / (px_w * 1000.0)


def perspective_skew_deg(corners: np.ndarray) -> float:
    top_w = np.linalg.norm(corners[1] - corners[0])
    bot_w = np.linalg.norm(corners[2] - corners[3])
    left_h = np.linalg.norm(corners[3] - corners[0])
    right_h = np.linalg.norm(corners[2] - corners[1])
    ratio_w = abs(top_w - bot_w) / max(top_w, bot_w, 1e-6)
    ratio_h = abs(left_h - right_h) / max(left_h, right_h, 1e-6)
    return float(math.degrees(math.atan(max(ratio_w, ratio_h))))


def horizontal_offset_ratio(corners: np.ndarray, img_w: int) -> float:
    cx = corners[:, 0].mean()
    return (cx - img_w / 2.0) / img_w


def coverage_ratio(corners: np.ndarray, img_shape: Tuple[int, int]) -> float:
    h, w = img_shape[:2]
    area = cv2.contourArea(corners.astype(np.float32))
    return float(area / (w * h))


def analyze_frame(frame: np.ndarray) -> GuidanceResult:
    res = GuidanceResult(corners=None)
    res.sharpness = laplacian_sharpness(frame)
    if res.sharpness < SHARPNESS_MIN:
        res.messages.append("Hold steady (image blurry)")

    corners = detect_board_corners(frame)
    res.corners = corners
    if corners is None:
        res.messages.append("Board not detected")
        return res

    h, w = frame.shape[:2]
    off = horizontal_offset_ratio(corners, w)
    if abs(off) > 0.10:
        res.messages.append("Move " + ("right" if off < 0 else "left"))

    dist = estimate_distance_m(corners, w)
    res.distance_m = dist
    lo, hi = CAPTURE_DISTANCE_RANGE_M
    if dist < lo:
        res.messages.append("Step farther")
    elif dist > hi:
        res.messages.append("Step closer")

    skew = perspective_skew_deg(corners)
    res.skew_deg = skew
    if skew > 15.0:
        # Wider/taller edge is the nearer one. Pick the dominant keystone axis
        # and tell the user which way to tilt to level the board.
        top_w = np.linalg.norm(corners[1] - corners[0])
        bot_w = np.linalg.norm(corners[2] - corners[3])
        left_h = np.linalg.norm(corners[3] - corners[0])
        right_h = np.linalg.norm(corners[2] - corners[1])
        dw = abs(top_w - bot_w) / max(top_w, bot_w, 1e-6)
        dh = abs(left_h - right_h) / max(left_h, right_h, 1e-6)
        if dw >= dh:
            direction = "up" if top_w > bot_w else "down"
        else:
            direction = "right" if left_h > right_h else "left"
        res.messages.append(f"Tilt {direction}")

    cov = coverage_ratio(corners, frame.shape)
    res.coverage = cov

    res.ready = (
        not res.messages
        and res.sharpness >= SHARPNESS_MIN
        and lo <= dist <= hi
        and skew <= 15.0
        and cov >= 0.90
    )
    if res.ready:
        res.messages.append("Ready")
    return res


def draw_overlay(frame: np.ndarray, result: GuidanceResult) -> np.ndarray:
    out = frame.copy()
    if result.corners is not None:
        pts = result.corners.astype(int).reshape(-1, 1, 2)
        color = (0, 255, 0) if result.ready else (0, 165, 255)
        cv2.polylines(out, [pts], True, color, 3)
    y = 30
    for m in result.messages:
        cv2.putText(out, m, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(out, m, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2, cv2.LINE_AA)
        y += 35
    return out
