from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Minimal .env loader: KEY=VALUE per line, # comments, no quotes required."""
    p = ROOT / ".env"
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


_load_dotenv()

DATA_DIR = Path(os.environ.get("STELLEGENT_DATA", ROOT / "data"))
DB_PATH = Path(os.environ.get("STELLEGENT_DB", ROOT / "stellegent.db"))

OCR_LANGS = ["en"]
OCR_CONFIDENCE_THRESHOLD = 0.75
SHARPNESS_MIN = 100.0
BOARD_PHYSICAL_MM = (2400.0, 1200.0)
CAPTURE_DISTANCE_RANGE_M = (1.5, 2.5)
RECTIFIED_SIZE = (1920, 1080)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "phi3:mini")

JWT_SECRET = os.environ.get(
    "STELLEGENT_JWT_SECRET",
    "change-me-in-prod-please-use-32-plus-chars-secret-key",
)
JWT_EXPIRY_MIN = 30

DATA_DIR.mkdir(parents=True, exist_ok=True)
