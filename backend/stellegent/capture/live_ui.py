"""Fullscreen live preview with overlays. Press SPACE to capture, q to quit."""
from __future__ import annotations
import cv2
from typing import Callable, Optional
import numpy as np

from .camera import open_camera
from .guidance import analyze_frame, draw_overlay


def run_live(on_capture: Callable[[np.ndarray], None],
             prefer_pi: bool = False, fullscreen: bool = True) -> None:
    cam = open_camera(prefer_pi=prefer_pi)
    win = "Stellegent Capture"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    if fullscreen:
        cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    try:
        while True:
            frame = cam.read()
            if frame is None:
                continue
            res = analyze_frame(frame)
            cv2.imshow(win, draw_overlay(frame, res))
            k = cv2.waitKey(1) & 0xFF
            if k == ord("q"):
                break
            if k == 32:  # SPACE
                on_capture(frame)
    finally:
        cam.release()
        cv2.destroyAllWindows()
