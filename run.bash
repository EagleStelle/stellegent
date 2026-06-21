#!/usr/bin/env bash
# Local dev launcher. Runtime state goes under data.
# Builds the SPA, then serves API + SPA on :8000.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"

# Config (JWT secret, GEMINI_API_KEY, OLLAMA_*, OCR_BACKEND) is read from .env by
# the app. These scripts only force runtime state under .local/data.
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[run] created .env from .env.example — edit it (GEMINI_API_KEY / JWT secret)"
fi

export STATIC_DIR="$ROOT/frontend/build"
mkdir -p "$ROOT/data"

# venv python (Unix or Git-Bash on Windows)
if [ -x ".venv/Scripts/python.exe" ]; then
  PY="$ROOT/.venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  echo "[run] creating venv + installing backend…"
  python3 -m venv .venv
  if [ -x ".venv/Scripts/python.exe" ]; then PY="$ROOT/.venv/Scripts/python.exe"; else PY="$ROOT/.venv/bin/python"; fi
  "$PY" -m pip install -q -e ./backend
fi

# build SPA if missing
if [ ! -f frontend/build/index.html ]; then
  echo "[run] building frontend…"
  (cd frontend && npm ci && npm run build)
fi

# migrate (run from backend/ so the new package wins)
( cd backend && "$PY" -m stellegent.cli initdb )

echo "[run] http://localhost:8000  (admin / admin123)"
cd backend
exec "$PY" -m uvicorn stellegent.main:app --host 0.0.0.0 --port 8000
