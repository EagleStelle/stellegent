import json
from pathlib import Path
import numpy as np

from stellegent.ocr.engine import OCRLine
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
    assert (d / "board.png").exists()
    assert (d / "lecture.docx").exists()
    assert (d / "lecture.pdf").exists()
    assert (d / "transcript.txt").exists()
    assert (d / "manifest.json").exists()
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert "math-equations" in m["tags"]
    assert len(m["lines"]) == 2
