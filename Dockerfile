FROM python:3.11-slim-bookworm AS builder

COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules

ENV PATH="/opt/venv/bin:/usr/local/bin:${PATH}" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_FUND=false

RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY backend/pyproject.toml backend/pyproject.toml

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/python -c "import pathlib, tomllib; print('\n'.join(tomllib.loads(pathlib.Path('backend/pyproject.toml').read_text())['project']['dependencies']))" > /tmp/requirements.txt \
    && /opt/venv/bin/pip install --no-compile -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt \
    && find /opt/venv -type d \( -name "__pycache__" -o -name "tests" -o -name "test" \) -prune -exec rm -rf '{}' + \
    && find /opt/venv -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

COPY frontend/package.json frontend/package-lock.json frontend/.npmrc frontend/

WORKDIR /build/frontend

RUN npm ci

COPY frontend/ ./

RUN npm run build

FROM python:3.11-slim-bookworm AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && install -d -o app -g app /app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=app:app /build/frontend/build /app/frontend/build
COPY --chown=app:app backend/stellegent /app/backend/stellegent
COPY backend/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh


EXPOSE 8000

# Entrypoint runs as root to repair bind-mount ownership, then drops to `app`.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["sh", "-c", "python -m stellegent.cli initdb && exec uvicorn stellegent.main:app --host 0.0.0.0 --port 8000"]
