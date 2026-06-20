# syntax=docker/dockerfile:1
# Single multi-stage image: stage 1 builds the SvelteKit SPA, stage 2 is the
# Python/FastAPI runtime that serves both the API and the built static SPA.
# Multi-arch base images (amd64 dev, arm64 Raspberry Pi 5).

# ---------- stage 1: build the SPA ----------
FROM node:22-bookworm-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json frontend/.npmrc ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # -> /fe/build (adapter-static, SPA fallback)

# ---------- stage 2: python runtime ----------
FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STATIC_DIR=/app/frontend/build \
    STELLEGENT_DATA=/data \
    STELLEGENT_DB=/data/stellegent.db

# OpenCV runtime libs (exactly one cv2 build; see pyproject note).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/ /app/backend/
RUN pip install -e /app/backend

# built SPA from stage 1
COPY --from=frontend /fe/build /app/frontend/build

VOLUME ["/data"]
EXPOSE 8000

# initdb is idempotent (migrations); run it then serve.
CMD ["sh", "-c", "python -m stellegent.cli initdb && uvicorn stellegent.main:app --host 0.0.0.0 --port 8000"]
