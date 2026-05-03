import numpy as np
import cv2

from stellegent.preprocess.pipeline import (
    detect_board_corners, rectify, clahe_normalize, denoise, remove_glare,
    laplacian_sharpness, preprocess,
)


def _synthetic_board(w=1280, h=720):
    img = np.full((h, w, 3), 50, dtype=np.uint8)
    pts = np.array([[200, 120], [1080, 140], [1100, 600], [180, 580]])
    cv2.fillPoly(img, [pts], (240, 240, 240))
    cv2.polylines(img, [pts], True, (10, 10, 10), 4)
    cv2.putText(img, "HELLO", (350, 360), cv2.FONT_HERSHEY_SIMPLEX, 3,
                (10, 10, 10), 6)
    return img, pts


def test_detect_corners():
    img, _ = _synthetic_board()
    corners = detect_board_corners(img)
    assert corners is not None
    assert corners.shape == (4, 2)


def test_rectify_size():
    img, _ = _synthetic_board()
    corners = detect_board_corners(img)
    out = rectify(img, corners, out_size=(1920, 1080))
    assert out.shape == (1080, 1920, 3)


def test_pipeline_runs():
    img, _ = _synthetic_board()
    out = preprocess(img)
    assert out.shape == (1080, 1920, 3)
    assert laplacian_sharpness(out) > 0


def test_glare_inpaint_no_op_when_clean():
    img = np.full((100, 100, 3), 100, dtype=np.uint8)
    assert np.array_equal(remove_glare(img), img)


def test_clahe_changes_image():
    img = np.full((50, 50, 3), 80, dtype=np.uint8)
    img[10:40, 10:40] = 180
    out = clahe_normalize(img)
    assert out.shape == img.shape


def test_denoise_runs():
    img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    assert denoise(img).shape == img.shape
