<p align="center">
  <img src="frontend/static/logo.svg" alt="Stellegent logo" width="96" height="96">
</p>

<h1 align="center">Stellegent</h1>

<p align="center">
  A whiteboard capture platform that turns classroom boards into searchable lecture records, summaries, and exportable documents.
</p>

## Overview

Stellegent captures or uploads whiteboard images, preprocesses them with OpenCV,
extracts text with a configurable OCR backend, generates corrected transcripts
and summaries, and stores the resulting lecture artifacts in SQLite. The
application ships as a FastAPI API with a SvelteKit single-page app, and can run
locally, in Docker, or on Raspberry Pi 5-class hardware.

## Features

- Whiteboard upload, live preview, and camera capture workflows.
- OCR via Google Gemini when configured, with RapidOCR/PP-OCR on ONNX Runtime as
  the offline fallback.
- Transcript correction, lecture summaries, course organization, annotations,
  and lecture search.
- Export formats: PDF, DOCX, TXT, source image, and JSON manifest.
- Role-based accounts for admins, professors, and students.
- Password auth, JWT cookies or bearer tokens, TOTP 2FA, Google sign-in, and
  email verification/reset support.
- Single-container production build that serves both the API and the web app.

## Tech Stack

| Area | Tools |
| --- | --- |
| Frontend | SvelteKit, TypeScript, Tailwind CSS, TanStack Query, openapi-fetch |
| Backend | FastAPI, Pydantic, Uvicorn, OpenCV, Pillow |
| OCR and NLP | Google Gemini, RapidOCR/PP-OCR, ONNX Runtime, Ollama |
| Data | SQLite with numbered SQL migrations |
| Deployment | Docker, Docker Compose, static SvelteKit build served by FastAPI |

## Repository Structure

```text
.
|-- backend/
|   |-- stellegent/          # FastAPI app, OCR pipeline, exports, database layer
|   |-- scripts/             # Development helpers
|   `-- tests/               # Backend test suite
|-- frontend/
|   |-- src/                 # SvelteKit app
|   `-- static/              # Public assets, including the project logo
|-- Dockerfile               # Production image: API + built SPA
|-- docker-compose.yml       # App service + Ollama service
|-- run.cmd                  # Windows development launcher
`-- run.bash                 # Unix/Git Bash local launcher
```

## Quick Start

The supplied Compose file starts Stellegent on port `8000` and an Ollama service
for the offline OCR fallback path.

```bash
cp .env.example .env
# Edit .env with your secrets, public URL, OAuth, email, and Gemini settings.
docker compose up -d
docker compose exec stellegent python -m stellegent.cli adduser admin "change-this-password" --role admin --email admin@example.com
```

Open <http://localhost:8000> and sign in with the admin account you created.

The Compose file reads deployment values from `.env` using `${...}` variable
substitution. For Gemini OCR, set `GEMINI_API_KEY` in `.env`; set
`GEMINI_MODELS` to use a comma-separated fallback order.
For production, replace the default `STELLEGENT_JWT_SECRET` with a unique
32-byte-or-longer value before exposing the app.

## Local Development

Create a local environment file, install the backend package, initialize the
database, and start FastAPI:

```bash
cp .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e "./backend[dev]"
python -m stellegent.cli initdb
python backend/scripts/seed_admin.py
python -m stellegent.cli serve --reload
```

For non-Docker local development, set `OLLAMA_HOST=http://127.0.0.1:11434` in
`.env` if Ollama is running on the host.

In a second terminal, start the SvelteKit dev server:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at <http://localhost:5173> and proxies API requests to
<http://localhost:8000>. Interactive API documentation is available at
<http://localhost:8000/docs>.

Convenience launchers are also included:

- `run.cmd` starts a Windows dev session with the web app on `:8000` and the API
  on `:8001`.
- `run.bash` builds the SPA and serves the combined app on `:8000`.

## Configuration

Runtime settings are read from environment variables. Docker Compose reads
`.env` for the `${...}` variables listed in `docker-compose.yml`; for local
development, the backend also reads `.env` directly.

| Variable | Purpose |
| --- | --- |
| `STELLEGENT_PORT` | Host port used by Docker Compose for the web/API container. |
| `STELLEGENT_JWT_SECRET` | JWT signing secret. Use a unique 32-byte-or-longer value outside development. |
| `STELLEGENT_DATA` | Directory for generated lecture artifacts. |
| `STELLEGENT_DB` | SQLite database path. |
| `STELLEGENT_RETENTION_AUDIT_DAYS` | Days to keep `audit_log` rows before the retention sweeper purges them (`0` = keep forever). Default `90`. |
| `STELLEGENT_RETENTION_SWEEP_HOURS` | Interval between retention sweeps (runs once at startup, then every N hours). Default `6`. |
| `OCR_BACKEND` | `auto`, `gemini`, or `paddle`. |
| `GEMINI_API_KEY` | Enables Gemini OCR when present. |
| `GEMINI_MODEL` | Gemini model name used by the OCR backend. |
| `GEMINI_MODELS` | Optional comma-separated Gemini OCR fallback order. Overrides `GEMINI_MODEL` when set. |
| `OLLAMA_HOST` | Ollama endpoint for local correction and summarization. |
| `OLLAMA_MODEL` | Local Ollama model used by the fallback path. |
| `OLLAMA_NUM_CTX` | Ollama context window. Lower values reduce VRAM/KV-cache use. |
| `OLLAMA_KEEP_ALIVE` | How long Ollama keeps the model loaded after a request. |
| `CORS_ORIGINS` | Comma-separated browser origins allowed during development. |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | Enables Google sign-in and account linking. |
| `RESEND_API_KEY` / `RESEND_FROM_EMAIL` | Enables production email delivery for verification and password reset flows. |

## CLI

```bash
python -m stellegent.cli initdb
python -m stellegent.cli adduser <username> <password> --role prof --email name@example.com
python -m stellegent.cli resetpw <email> <new-password>
python -m stellegent.cli process path/to/whiteboard.jpg --course CS101
python -m stellegent.cli capture --pi --fullscreen
python -m stellegent.cli serve --reload
```

## API

The API is mounted under `/api/v1`. Use `/docs` for the generated OpenAPI UI and
`/openapi.json` for client generation.

The frontend type client can be regenerated from a running backend:

```bash
cd frontend
npm run gen:api
```

## Testing

```bash
pip install -e "./backend[dev]"
pytest backend/tests
```

## Deployment Notes

- Run behind HTTPS in production and use a unique JWT secret.
- Configure a verified Resend sender before enabling production email flows.
- USB webcams in Docker require the device to be passed into the container.
- CSI cameras on Raspberry Pi require host `libcamera`/`picamera2`; for native
  Pi capture, create the Python environment with access to system packages and
  run `python -m stellegent.cli capture --pi`.
- The offline fallback path uses ONNX Runtime to avoid ARM64 PaddlePaddle wheel
  issues.
- A background retention sweeper runs on startup and every
  `STELLEGENT_RETENTION_SWEEP_HOURS`: it always deletes used/expired password
  reset and email verification tokens, and purges `audit_log` rows older than
  `STELLEGENT_RETENTION_AUDIT_DAYS`. User content (lectures, courses, accounts)
  is never auto-deleted.

## Credits

- DejaVu Sans and DejaVu Sans Bold are bundled in
  `backend/stellegent/export/assets/fonts` for PDF generation. DejaVu fonts are
  provided by the DejaVu Fonts project.
- Stellegent is built on FastAPI, SvelteKit, Tailwind CSS, RapidOCR/PP-OCR, ONNX
  Runtime, OpenCV, Ollama, Google Gemini, lucide, and Phosphor Icons.
