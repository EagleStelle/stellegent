# Stellegent

Whiteboard-to-document capture system targeting the Raspberry Pi 5. Captures a
classroom whiteboard, preprocesses the image, performs OCR, applies
LLM-assisted correction, generates a summary, exports DOCX/PDF/TXT/PNG + a JSON
manifest, stores everything in SQLite, and serves it through a typed REST API
and a single-page web app.

**OCR is pluggable.** The primary engine is **Google Gemini** (vision) via the
`google-genai` SDK; the fallback is **PP-OCR** run through RapidOCR on the
onnxruntime backend (PaddlePaddle's PyPI aarch64 wheels segfault on the Pi 5, so
onnxruntime runs the same PP-OCR weights exported to ONNX). The fallback path's
correction/summary use Phi-3-mini via Ollama; Gemini self-corrects in one call.

## Stack

| Layer     | Tech                                                                   |
| --------- | ---------------------------------------------------------------------- |
| Frontend  | SvelteKit (SPA / `adapter-static`) · TypeScript · Tailwind v4 · shadcn-svelte · bits-ui · lucide · TanStack Query · openapi-fetch |
| Backend   | FastAPI · Pydantic · Uvicorn · OpenCV · RapidOCR/onnxruntime · google-genai · Ollama |
| Data      | SQLite + SQL schema migrations                                        |
| Auth      | Local email + password, bcrypt, JWT (HttpOnly cookie + Bearer), TOTP authenticator 2FA, Google OAuth/OIDC sign-in |
| Deploy    | One multi-stage Docker image (Node build → Python runtime serves API + SPA) + Ollama |

## Layout

```
.
├── backend/                  # FastAPI app (python package: stellegent)
│   ├── pyproject.toml
│   ├── stellegent/
│   │   ├── main.py           # app + /api/v1 + serves built SPA
│   │   ├── config.py         # pydantic-settings
│   │   ├── api/v1/           # auth, lectures, capture, audit routers
│   │   ├── schemas/          # pydantic models (drive the OpenAPI schema)
│   │   ├── core/security.py  # JWT
│   │   ├── deps.py           # auth dependencies
│   │   ├── db/               # store + migrate.py + migrations/*.sql
│   │   ├── ocr/              # base + gemini (primary) + paddle (fallback)
│   │   ├── preprocess/ nlp/ export/ capture/
│   │   ├── pipeline.py  cli.py
│   ├── scripts/  tests/
├── frontend/                 # SvelteKit SPA
│   └── src/{routes,lib}
├── Dockerfile                # single multi-stage image
├── docker-compose.yml        # app + ollama
└── .env.example
```

---

## Quick start (Docker)

```bash
cp .env.example .env          # set STELLEGENT_JWT_SECRET, GEMINI_API_KEY, optional Google OAuth
docker compose up --build
docker compose exec ollama ollama pull phi3:mini   # only needed for PP-OCR fallback
docker compose exec app python backend/scripts/seed_admin.py
```

Open <http://localhost:8000>. Log in as `admin@example.com / admin123` (change before
deploying). The image builds the SPA and serves it from FastAPI, so it is one
origin / one container (plus Ollama).

---

## Local development

Two processes: FastAPI (`:8000`) and the Vite dev server (`:5173`, proxies
`/api` to the backend).

### Backend

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows; or: source .venv/bin/activate
pip install -e ./backend
cp .env.example .env                # set GEMINI_API_KEY (or OCR_BACKEND=paddle)
python -m stellegent.cli initdb     # applies the schema baseline
python backend/scripts/seed_admin.py
python -m stellegent.cli serve --reload   # http://localhost:8000  (docs: /docs)
```

### Frontend

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173
npm run gen:api                     # regenerate typed API client from the running backend
```

`npm run gen:api` runs `openapi-typescript` against `http://localhost:8000/openapi.json`
and writes `src/lib/api/schema.d.ts`, giving the `openapi-fetch` client end-to-end types.

---

## Configuration (`.env`, repo root)

| Variable                | Default                  | Purpose                                            |
| ----------------------- | ------------------------ | -------------------------------------------------- |
| `STELLEGENT_JWT_SECRET` | built-in dev default     | JWT signing key. Must be ≥ 32 bytes.               |
| `GOOGLE_OAUTH_CLIENT_ID` | (empty) | Google OAuth web client ID                         |
| `GOOGLE_OAUTH_CLIENT_SECRET` | (empty) | Google OAuth web client secret                     |
| `GOOGLE_ALLOWED_DOMAIN` | (empty) | Optional hosted-domain restriction                 |
| `RESEND_API_KEY` | (empty) | Resend API key for transactional email             |
| `RESEND_FROM_EMAIL` | `Stellegent <onboarding@resend.dev>` | Verified sender address             |
| `RESEND_REPLY_TO` | (empty) | Optional reply-to address                          |
| `STELLEGENT_DATA`       | `./data`                 | Capture artefacts root                             |
| `STELLEGENT_DB`         | `./data/stellegent.db`   | SQLite path                                        |
| `OCR_BACKEND`           | `auto`                   | `auto` \| `gemini` \| `paddle`                     |
| `GEMINI_API_KEY`        | (empty)                  | Google AI Studio key; enables Gemini in `auto`     |
| `GEMINI_MODEL`          | `gemini-2.5-flash`       | Gemini model tag                                   |
| `OLLAMA_HOST`           | `http://127.0.0.1:11434` | Ollama endpoint (PP-OCR fallback NLP)              |
| `OLLAMA_MODEL`          | `phi3:mini`              | Ollama model tag                                   |
| `CORS_ORIGINS`          | `http://localhost:5173`  | Allowed dev origins (comma-separated)              |

`auto` uses Gemini when `GEMINI_API_KEY` is set, otherwise PP-OCR; if a Gemini
call fails at runtime it falls back to PP-OCR for that request.

For local Svelte dev with Google OAuth, register
`http://localhost:5173/api/v1/auth/google/callback` in Google Cloud Console.
The app derives its public URL from browser/proxy headers, marks cookies secure
when the request is HTTPS, and adds HSTS only on HTTPS responses. For public
deployment, use HTTPS and a unique 32+ byte JWT secret.
For Resend, set `RESEND_API_KEY` and a verified `RESEND_FROM_EMAIL`. If Resend
is not configured in local development, reset and verification endpoints return
dev-only tokens so the flows can still be tested.

---

## API (`/api/v1`)

```
POST   /login           {email,password}           -> {token,role,username} (+cookie)
POST   /login/mfa       {code,mfa_token?}           -> completes 2FA challenge
POST   /register        {username,email,password}  -> creates a 'student', username stores full name
POST   /logout
GET    /me
GET    /account                                     current account/security settings
PATCH  /account        {username,email}
POST   /account/password {current_password,new_password}
POST   /account/email/verification                  -> send verification email
POST   /verify-email   {token}
POST   /account/2fa/setup                           -> otpauth URI + QR data URL
POST   /account/2fa/enable {code}                   -> enables TOTP + recovery codes
POST   /account/2fa/disable {code,current_password?}
GET    /auth/google/start?mode=login|link           Google OAuth redirect
GET    /auth/google/callback                        Google OAuth callback
POST   /forgot-password {email}                    -> sends reset email, returns token only in dev
POST   /reset-password  {token,password}
GET    /lectures?date=&course=&q=
GET    /lectures/{id}
GET    /lectures/{id}/file?type=pdf|docx|txt|image|manifest
POST   /lectures/{id}/annotate   {note}
DELETE /lectures/{id}                               prof|admin
POST   /upload          multipart image + course   prof|admin
POST   /capture         {course}                   prof|admin (shared camera)
GET    /stream          MJPEG live preview          prof|admin
GET    /guidance        framing guidance JSON       prof|admin
GET    /audit                                       admin
```

Interactive docs at `/docs`. Auth via `Authorization: Bearer <jwt>` or the
`token` cookie; tokens expire after 30 minutes.

---

## Database Schema

Fresh deploys start from `backend/stellegent/db/migrations/001_init.sql`.
`initdb` and app startup apply the schema idempotently and track applied files
in `schema_version`. Add a new numbered file only when evolving an existing
deployment.

---

## CLI

```bash
python -m stellegent.cli initdb
python -m stellegent.cli adduser <user> <pass> --role prof --email a@b.com
python -m stellegent.cli resetpw <email> <newpass>      # offline password reset
python -m stellegent.cli process path/to/image.jpg --course CS101
python -m stellegent.cli capture --pi --fullscreen      # native OpenCV window
python -m stellegent.cli serve --reload
```

---

## Tests

```bash
pip install -e "./backend[dev]"
pytest backend/tests
```

---

## Known constraints

- **One OpenCV build only.** Multiple `cv2` wheels leave duplicate native
  symbols that `SIGSEGV` on ARM64. `pyproject.toml` pins only `opencv-python`
  (RapidOCR depends on it). NumPy is pinned `<2` for OpenCV `<4.11` ABI.
- **OCR fallback on the Pi** uses `rapidocr-onnxruntime` (onnxruntime, stable on
  aarch64). PaddlePaddle's aarch64 wheels segfault during inference.
- **Camera in Docker is the hard part.** USB webcams work by mapping
  `/dev/video0` into the `app` container. CSI cameras (Camera Module 3 /
  `imx708`) are only reachable via `libcamera`/`picamera2`, which is not
  pip-installable and needs device + udev mounts inside the image — see the
  commented `devices:` block in `docker-compose.yml`. For native (non-Docker)
  Pi capture, create the venv with `--system-site-packages` so it can import the
  apt-installed `python3-picamera2`, and run `python -m stellegent.cli capture --pi`.
- **Gemini returns plain text** (no per-line bbox/confidence), so its path skips
  the confidence-gated correction step and feeds clean text straight to the
  summarizer. PP-OCR keeps the per-line confidence gating.
- **Phi-3-mini on the Pi is the slowest stage** of the fallback path; pre-pull it
  so it stays warm. Gemini moves that work off-device.
