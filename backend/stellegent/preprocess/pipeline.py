"""Image preprocessing pipeline: detect board, rectify, deglare, binarize."""
from __future__ import annotations
import cv2
import numpy as np
from typing import Optional, Tuple

from ..config import RECTIFIED_SIZE


# ---------- corner detection ----------

def _order_corners(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def _board_mask(img: np.ndarray) -> np.ndarray:
    """Whiteboard surface = bright + low saturation. Returns binary mask."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    mask = ((s < 60) & (v > 140)).astype(np.uint8) * 255
    k = np.ones((9, 9), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
    return mask


def _largest_quad(mask: np.ndarray, img_area: float) -> Optional[np.ndarray]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.15 * img_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if area > 0.98 * img_area and x <= 1 and y <= 1:
            continue
        peri = cv2.arcLength(c, True)
        for eps in (0.01, 0.02, 0.03, 0.05, 0.08):
            approx = cv2.approxPolyDP(c, eps * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                return _order_corners(approx)
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect)
        return _order_corners(box.astype(np.float32))
    return None


def detect_board_corners(img: np.ndarray) -> Optional[np.ndarray]:
    """Find 4 corners of the whiteboard. Tries color mask first, then edges."""
    h, w = img.shape[:2]
    img_area = float(h * w)

    quad = _largest_quad(_board_mask(img), img_area)
    if quad is not None:
        return quad

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    return _largest_quad(edges, img_area)


# ---------- rectify ----------

def rectify(img: np.ndarray, corners: np.ndarray,
            out_size: Tuple[int, int] = RECTIFIED_SIZE) -> np.ndarray:
    w, h = out_size
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    H, _ = cv2.findHomography(corners, dst)
    return cv2.warpPerspective(img, H, (w, h))


def crop_to_board_mask(img: np.ndarray) -> np.ndarray:
    """Fallback when corners aren't found: tight-crop bounding box of board mask."""
    mask = _board_mask(img)
    ys, xs = np.where(mask > 0)
    if xs.size == 0:
        return cv2.resize(img, RECTIFIED_SIZE)
    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()
    cropped = img[y0:y1 + 1, x0:x1 + 1]
    return cv2.resize(cropped, RECTIFIED_SIZE)


# ---------- enhancement ----------

def remove_glare(gray: np.ndarray, thresh: int = 250,
                 max_blob_ratio: float = 0.02,
                 max_total_ratio: float = 0.10) -> np.ndarray:
    """Inpaint small specular highlights on a grayscale image."""
    _, raw_mask = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    h, w = gray.shape
    img_area = h * w
    n, labels, stats, _ = cv2.connectedComponentsWithStats(raw_mask, connectivity=8)
    blob_limit = max_blob_ratio * img_area
    mask = np.zeros_like(raw_mask)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < blob_limit:
            mask[labels == i] = 255
    if cv2.countNonZero(mask) == 0:
        return gray
    if cv2.countNonZero(mask) > max_total_ratio * img_area:
        return gray
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
    return cv2.inpaint(gray, mask, 5, cv2.INPAINT_NS)


def shadow_normalize(gray: np.ndarray) -> np.ndarray:
    """Estimate background illumination and divide it out so writing pops."""
    bg = cv2.medianBlur(gray, 51)
    bg = np.where(bg == 0, 1, bg).astype(np.float32)
    norm = (gray.astype(np.float32) / bg) * 200.0
    return np.clip(norm, 0, 255).astype(np.uint8)


def binarize(gray: np.ndarray) -> np.ndarray:
    """Adaptive threshold -> clean black writing on white. For display/export only.
    Do NOT feed to PaddleOCR; the recognizer needs anti-aliased strokes."""
    gray = cv2.bilateralFilter(gray, 5, 50, 50)
    bin_img = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        blockSize=31, C=15,
    )
    bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN,
                               np.ones((2, 2), np.uint8), iterations=1)
    return bin_img


def enhance_for_ocr(gray: np.ndarray) -> np.ndarray:
    """Soft enhancement that PaddleOCR likes: flatten lighting, boost contrast,
    sharpen — but keep grayscale gradients (no hard threshold)."""
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16, 16))
    g = clahe.apply(gray)
    # Mild unsharp mask — sharpens stroke edges without halos.
    blur = cv2.GaussianBlur(g, (0, 0), sigmaX=1.2)
    g = cv2.addWeighted(g, 1.6, blur, -0.6, 0)
    return g


def laplacian_sharpness(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


# ---------- top-level ----------

def preprocess(img: np.ndarray, corners: Optional[np.ndarray] = None) -> np.ndarray:
    """Full pipeline tuned for PaddleOCR PP-OCRv5: rectify, deglare, flatten
    lighting, CLAHE + unsharp. Returns 3-ch BGR grayscale (NOT binary).
    Strokes keep anti-aliasing the recognizer was trained on."""
    if corners is None:
        corners = detect_board_corners(img)
    if corners is not None:
        rect = rectify(img, corners)
    else:
        rect = crop_to_board_mask(img)

    gray = cv2.cvtColor(rect, cv2.COLOR_BGR2GRAY)
    gray = remove_glare(gray)
    gray = shadow_normalize(gray)
    gray = enhance_for_ocr(gray)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def preprocess_for_export(img: np.ndarray,
                          corners: Optional[np.ndarray] = None) -> np.ndarray:
    """Hard B&W version for human-readable exports (PNG attached to lecture)."""
    if corners is None:
        corners = detect_board_corners(img)
    rect = rectify(img, corners) if corners is not None else crop_to_board_mask(img)
    gray = cv2.cvtColor(rect, cv2.COLOR_BGR2GRAY)
    gray = remove_glare(gray)
    gray = shadow_normalize(gray)
    return cv2.cvtColor(binarize(gray), cv2.COLOR_GRAY2BGR)
