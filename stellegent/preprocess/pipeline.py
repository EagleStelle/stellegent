"""Image preprocessing pipeline: detect board, rectify, denoise, deglare."""
from __future__ import annotations
import cv2
import numpy as np
from typing import Optional, Tuple

from ..config import RECTIFIED_SIZE


def _order_corners(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def detect_board_corners(img: np.ndarray) -> Optional[np.ndarray]:
    """Find 4 corners of largest quadrilateral. Returns None if not found."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    img_area = img.shape[0] * img.shape[1]
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > 0.1 * img_area:
            return _order_corners(approx)
    return None


def rectify(img: np.ndarray, corners: np.ndarray,
            out_size: Tuple[int, int] = RECTIFIED_SIZE) -> np.ndarray:
    w, h = out_size
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    H, _ = cv2.findHomography(corners, dst)
    return cv2.warpPerspective(img, H, (w, h))


def clahe_normalize(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def denoise(img: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(img, (5, 5), 0)


def remove_glare(img: np.ndarray, thresh: int = 240) -> np.ndarray:
    """Inpaint bright glare spots using Navier-Stokes."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)
    if cv2.countNonZero(mask) == 0:
        return img
    return cv2.inpaint(img, mask, 5, cv2.INPAINT_NS)


def laplacian_sharpness(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def preprocess(img: np.ndarray, corners: Optional[np.ndarray] = None) -> np.ndarray:
    """Full pipeline. If corners None, attempts auto-detection."""
    if corners is None:
        corners = detect_board_corners(img)
    if corners is not None:
        img = rectify(img, corners)
    else:
        img = cv2.resize(img, RECTIFIED_SIZE)
    img = remove_glare(img)
    img = clahe_normalize(img)
    img = denoise(img)
    return img
