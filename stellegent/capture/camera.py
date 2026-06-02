"""Camera abstraction. picamera2 on RPi, cv2.VideoCapture elsewhere."""
from __future__ import annotations
import sys
import cv2
import numpy as np
from typing import Optional


class Camera:
    def read(self) -> Optional[np.ndarray]:
        raise NotImplementedError

    def release(self) -> None:
        raise NotImplementedError


class CV2Camera(Camera):
    def __init__(self, index: int = 0, width: int = 1920, height: int = 1080):
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.cap.isOpened():
            raise RuntimeError(f"cannot open camera index {index}")

    def read(self) -> Optional[np.ndarray]:
        ok, frame = self.cap.read()
        return frame if ok else None

    def release(self) -> None:
        self.cap.release()


class PiCamera2(Camera):
    def __init__(self, width: int = 1920, height: int = 1080):
        from picamera2 import Picamera2  # type: ignore
        self.picam = Picamera2()
        cfg = self.picam.create_still_configuration(main={"size": (width, height)})
        self.picam.configure(cfg)
        self.picam.start()

    def read(self) -> Optional[np.ndarray]:
        arr = self.picam.capture_array()
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    def release(self) -> None:
        self.picam.stop()


def is_raspberry_pi() -> bool:
    try:
        with open("/proc/device-tree/model", "r") as f:
            return "raspberry pi" in f.read().lower()
    except OSError:
        return False


def open_camera(prefer_pi: bool = False, index: int = 0) -> Camera:
    # CSI cameras (e.g. RPi Cam v3) only work via libcamera/picamera2, not cv2.
    # On a Pi, default to picamera2 even if caller didn't pass --pi.
    if prefer_pi or is_raspberry_pi():
        try:
            return PiCamera2()
        except Exception as e:
            print(f"[camera] picamera2 unavailable ({e!r}); falling back to cv2",
                  file=sys.stderr)
    return CV2Camera(index=index)
