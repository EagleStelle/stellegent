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

    # Initial admin account (auto-provisioned on startup if no admin exists)
    admin_email: str = Field("admin@example.com", validation_alias="ADMIN_EMAIL")
    admin_password: str = Field("admin123", validation_alias="ADMIN_PASSWORD")

    jwt_secret: str = Field(
        "change-me-in-prod-please-use-32-plus-chars-secret-key",
        validation_alias="STELLEGENT_JWT_SECRET",
    )
    jwt_expiry_min: int = Field(30, validation_alias="STELLEGENT_JWT_EXPIRY_MIN")
    app_name: str = Field("Stellegent", validation_alias="STELLEGENT_APP_NAME")
    public_base_url: str = Field("", validation_alias="STELLEGENT_PUBLIC_BASE_URL")
    cookie_secure: bool = Field(False, validation_alias="STELLEGENT_COOKIE_SECURE")
    cookie_samesite: str = Field("lax", validation_alias="STELLEGENT_COOKIE_SAMESITE")
    require_secure_config: bool = Field(
        False, validation_alias="STELLEGENT_REQUIRE_SECURE_CONFIG"
    )
    security_headers: bool = Field(True, validation_alias="STELLEGENT_SECURITY_HEADERS")
    security_hsts_enabled: bool = Field(
        False, validation_alias="STELLEGENT_SECURITY_HSTS"
    )

    # Google OAuth / Sign in with Google.
    google_oauth_client_id: str = Field(
        "", validation_alias="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_oauth_client_secret: str = Field(
        "", validation_alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    google_oauth_redirect_uri: str = Field(
        "", validation_alias="GOOGLE_OAUTH_REDIRECT_URI"
    )
    google_allowed_domain: str = Field(
        "", validation_alias="GOOGLE_ALLOWED_DOMAIN"
    )

    # Transactional email via Resend.
    resend_api_key: str = Field("", validation_alias="RESEND_API_KEY")
    resend_from_email: str = Field(
        "Stellegent <onboarding@resend.dev>",
        validation_alias="RESEND_FROM_EMAIL",
    )
    email_reply_to: str = Field("", validation_alias="RESEND_REPLY_TO")

    # OCR backend selection: auto | gemini | paddle
    ocr_backend: str = Field("auto", validation_alias="OCR_BACKEND")
    gemini_api_key: str = Field("", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", validation_alias="GEMINI_MODEL")
    gemini_models: str = Field("", validation_alias="GEMINI_MODELS")

    # Local NLP (Ollama)
    ollama_host: str = Field("http://127.0.0.1:11434", validation_alias="OLLAMA_HOST")
    ollama_model: str = Field("phi3:mini", validation_alias="OLLAMA_MODEL")
    ollama_auto_pull: bool = Field(True, validation_alias="OLLAMA_AUTO_PULL")
    ollama_pull_timeout_sec: int = Field(1800, validation_alias="OLLAMA_PULL_TIMEOUT")
    # Per-request generate/chat timeout. Slow CPU-only NAS needs minutes for a
    # full summary, so default well past the old hard-coded 120s.
    ollama_request_timeout_sec: int = Field(
        600, validation_alias="OLLAMA_REQUEST_TIMEOUT"
    )
    # Context size drives KV-cache memory. Smaller values keep 4 GB GPUs from
    # spilling as much work back to CPU.
    ollama_num_ctx: int = Field(4096, validation_alias="OLLAMA_NUM_CTX")
    ollama_keep_alive: str = Field("5m", validation_alias="OLLAMA_KEEP_ALIVE")

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

    @property
    def gemini_model_list(self) -> Tuple[str, ...]:
        raw = self.gemini_models or self.gemini_model
        models = []
        seen = set()
        for model in raw.split(","):
            model = model.strip()
            if not model or model in seen:
                continue
            models.append(model)
            seen.add(model)
        return tuple(models)


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
OLLAMA_AUTO_PULL = settings.ollama_auto_pull
OLLAMA_PULL_TIMEOUT = settings.ollama_pull_timeout_sec
OLLAMA_REQUEST_TIMEOUT = settings.ollama_request_timeout_sec
OLLAMA_NUM_CTX = settings.ollama_num_ctx
OLLAMA_KEEP_ALIVE = settings.ollama_keep_alive
JWT_SECRET = settings.jwt_secret
JWT_EXPIRY_MIN = settings.jwt_expiry_min
APP_NAME = settings.app_name

DATA_DIR.mkdir(parents=True, exist_ok=True)
