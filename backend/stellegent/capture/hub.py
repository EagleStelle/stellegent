"""Shared camera + MJPEG generator + cached guidance for browser live UI."""
from __future__ import annotations
import threading
import time
from dataclasses import asdict
from typing import Optional, Tuple

import cv2
import numpy as np

from .camera import open_camera, Camera
from .guidance import analyze_frame, draw_overlay, GuidanceResult


class CameraHub:
    def __init__(self, prefer_pi: bool = False):
        self.prefer_pi = prefer_pi
        self._cam: Optional[Camera] = None
        self._lock = threading.Lock()
        self._last_frame: Optional[np.ndarray] = None
        self._last_guidance: Optional[GuidanceResult] = None
        self._last_t: float = 0.0

    def _ensure(self) -> Camera:
        if self._cam is None:
            self._cam = open_camera(prefer_pi=self.prefer_pi)
        return self._cam

    def read(self) -> Optional[np.ndarray]:
        with self._lock:
            cam = self._ensure()
            frame = cam.read()
            if frame is not None:
                self._last_frame = frame
            return frame

    def snapshot(self) -> Optional[np.ndarray]:
        return self.read()

    def guidance(self, max_age: float = 0.2) -> Tuple[Optional[np.ndarray], GuidanceResult]:
        now = time.time()
        if self._last_guidance and (now - self._last_t) < max_age and self._last_frame is not None:
            return self._last_frame, self._last_guidance
        frame = self.read()
        if frame is None:
            return None, GuidanceResult(corners=None, messages=["No camera frame"])
        g = analyze_frame(frame)
        self._last_guidance = g
        self._last_t = now
        return frame, g

    def mjpeg(self, fps: int = 12, overlay: bool = True):
        boundary = b"--frame"
        delay = 1.0 / max(1, fps)
        while True:
            frame = self.read()
            if frame is None:
                time.sleep(delay)
                continue
            if overlay:
                g = analyze_frame(frame)
                self._last_guidance = g
                self._last_t = time.time()
                frame = draw_overlay(frame, g)
            ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ok:
                continue
            yield (boundary + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                   + str(len(jpg)).encode() + b"\r\n\r\n" + jpg.tobytes() + b"\r\n")
            time.sleep(delay)

    def release(self) -> None:
        with self._lock:
            if self._cam is not None:
                try:
                    self._cam.release()
                except Exception:
                    pass
                self._cam = None


_HUB: Optional[CameraHub] = None
_HUB_LOCK = threading.Lock()


def get_hub(prefer_pi: bool = False) -> CameraHub:
    global _HUB
    with _HUB_LOCK:
        if _HUB is None:
            _HUB = CameraHub(prefer_pi=prefer_pi)
        return _HUB


def guidance_to_dict(g: GuidanceResult) -> dict:
    return {
        "messages": list(g.messages),
        "ready": bool(g.ready),
        "sharpness": g.sharpness,
        "distance_m": g.distance_m,
        "skew_deg": g.skew_deg,
        "coverage": g.coverage,
        "has_board": g.corners is not None,
    }
