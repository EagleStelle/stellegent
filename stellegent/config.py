from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent.parent
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

JWT_SECRET = os.environ.get("STELLEGENT_JWT_SECRET", "change-me-in-prod")
JWT_EXPIRY_MIN = 30

DATA_DIR.mkdir(parents=True, exist_ok=True)
