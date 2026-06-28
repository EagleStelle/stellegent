from pathlib import Path
import numpy as np

from stellegent.ocr.base import OCRLine
from stellegent.export import export_all


def test_export_all(tmp_path):
    img = np.full((1080, 1920, 3), 230, dtype=np.uint8)
    lines = [
        OCRLine("Hello world", 0.95, [[0, 0], [200, 0], [200, 50], [0, 50]]),
        OCRLine("x = 2 + 3", 0.5, [[0, 60], [200, 60], [200, 110], [0, 110]]),
    ]
    res = export_all(img, lines, "Hello world\nx = 2 + 3", "- intro",
                     base_dir=tmp_path, course_name="Math")
    d = Path(res.dir)
    assert (d / "board.webp").exists()
    assert (d / "board_raw.webp").exists()
    assert (d / "lecture.docx").exists()
    assert (d / "lecture.pdf").exists()
    assert (d / "transcript.txt").exists()
    # documents carry summary + transcript only — no embedded image
    txt = (d / "transcript.txt").read_text("utf-8")
    assert "Summary" in txt and "Transcript" in txt
    assert "- intro" in txt
    assert "math-equations" in res.tags
