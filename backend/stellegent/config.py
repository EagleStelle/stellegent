"""Typed settings (pydantic-settings) + derived constants.

Env file is the repo-root ``.env`` (one level above ``backend/``). Process env
overrides file values. Relative ``STELLEGENT_DATA`` / ``STELLEGENT_DB`` paths
resolve against the repo root, matching the old Flask behaviour.
"""
from __future__ import annotations
from pathlib import Path
from typing import Tuple

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# repo-root/  (backend/stellegent/config.py -> repo root is parents[2])
ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    data_dir: Path = Field(Path("data"), validation_alias="STELLEGENT_DATA")
    # Keep all runtime state under data/ (one gitignored dir / one Docker volume).
    db_path: Path = Field(Path("data/stellegent.db"), validation_alias="STELLEGENT_DB")

    jwt_secret: str = Field(
        "change-me-in-prod-please-use-32-plus-chars-secret-key",
        validation_alias="STELLEGENT_JWT_SECRET",
    )
    jwt_expiry_min: int = Field(30, validation_alias="STELLEGENT_JWT_EXPIRY_MIN")

    # OCR backend selection: auto | gemini | paddle
    ocr_backend: str = Field("auto", validation_alias="OCR_BACKEND")
    gemini_api_key: str = Field("", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", validation_alias="GEMINI_MODEL")

    # Local NLP (Ollama)
    ollama_host: str = Field("http://127.0.0.1:11434", validation_alias="OLLAMA_HOST")
    ollama_model: str = Field("phi3:mini", validation_alias="OLLAMA_MODEL")

    # CORS origin for the SvelteKit dev server (prod serves SPA same-origin)
    cors_origins: str = Field("http://localhost:5173", validation_alias="CORS_ORIGINS")

    def _resolve(self, p: Path) -> Path:
        p = Path(p)
        return p if p.is_absolute() else (ROOT / p).resolve()

    @property
    def data_path(self) -> Path:
        return self._resolve(self.data_dir)

    @property
    def db_file(self) -> Path:
        return self._resolve(self.db_path)


settings = Settings()

# ---- legacy module-level constants (kept so ported modules import unchanged) ----
DATA_DIR: Path = settings.data_path
DB_PATH: Path = settings.db_file
OCR_CONFIDENCE_THRESHOLD: float = 0.75
OCR_LANGS = ["en"]
SHARPNESS_MIN: float = 100.0
BOARD_PHYSICAL_MM: Tuple[float, float] = (2400.0, 1200.0)
CAPTURE_DISTANCE_RANGE_M: Tuple[float, float] = (1.5, 2.5)
RECTIFIED_SIZE: Tuple[int, int] = (1920, 1080)
OLLAMA_HOST = settings.ollama_host
OLLAMA_MODEL = settings.ollama_model
JWT_SECRET = settings.jwt_secret
JWT_EXPIRY_MIN = settings.jwt_expiry_min

DATA_DIR.mkdir(parents=True, exist_ok=True)
