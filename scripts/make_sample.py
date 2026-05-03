"""Generate a synthetic whiteboard image at samples/board.jpg for smoke tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "samples" / "board.jpg"
OUT.parent.mkdir(parents=True, exist_ok=True)

w, h = 1600, 1000
img = np.full((h, w, 3), 60, dtype=np.uint8)  # dark wall
board = np.array([[180, 120], [1420, 140], [1440, 880], [160, 870]])
cv2.fillPoly(img, [board], (245, 245, 245))   # whiteboard
cv2.polylines(img, [board], True, (20, 20, 20), 6)

font = cv2.FONT_HERSHEY_SIMPLEX
ink = (15, 15, 15)
lines = [
    ("Lecture 3: Linear Algebra", 240, 240, 1.4, 3),
    ("1. Matrix multiplication", 260, 340, 1.0, 2),
    ("   A * B != B * A", 260, 400, 0.9, 2),
    ("2. Determinant: det(AB) = det(A)det(B)", 260, 480, 0.9, 2),
    ("3. Eigen: A v = lambda v", 260, 560, 0.9, 2),
    ("Example: x = 2 + 3", 260, 660, 0.9, 2),
    ("- Symmetric matrices", 260, 740, 0.8, 2),
    ("- Orthogonal basis", 260, 800, 0.8, 2),
]
for text, x, y, scale, thick in lines:
    cv2.putText(img, text, (x, y), font, scale, ink, thick, cv2.LINE_AA)

cv2.imwrite(str(OUT), img)
print(f"wrote {OUT}")
