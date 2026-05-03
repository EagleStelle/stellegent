# Stellegent

Portable, offline whiteboard-to-document system. RPi 5 target. Captures classroom whiteboard, preprocesses, OCRs, corrects + summarizes via local LLM, exports DOCX/PDF/TXT, stores in SQLite, browses via Flask web UI.

## Modules

| #   | Module                                             | Path                                          |
| --- | -------------------------------------------------- | --------------------------------------------- |
| 1   | Capture + live preview                             | `stellegent/capture/`                         |
| 2   | Preprocessing                                      | `stellegent/preprocess/`                      |
| 3   | OCR (PaddleOCR / EasyOCR)                          | `stellegent/ocr/`                             |
| 4   | NLP correct + summarize (Ollama / SymSpell + sumy) | `stellegent/nlp/`                             |
| 5   | Export DOCX/PDF/TXT/JSON                           | `stellegent/export/`                          |
| 6   | SQLite store                                       | `stellegent/db/`                              |
| 7   | Flask web + JWT auth                               | `stellegent/web/`                             |
| —   | Orchestrator + CLI                                 | `stellegent/pipeline.py`, `stellegent/cli.py` |

## Install

### Windows dev

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_dev.ps1
.\.venv\Scripts\Activate.ps1
```

### Raspberry Pi 5 (Bookworm 64-bit)

```bash
bash scripts/install_rpi.sh
source .venv/bin/activate
```

Pulls `phi3:mini` via Ollama. If pull fails, run `ollama pull phi3:mini` manually. PaddleOCR may need `paddlepaddle` ARM wheels — fall back to EasyOCR by default if init fails (handled automatically).

## Quick start

Always activate the venv first so `stellegent` and its deps are importable:

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/RPi:

```bash
source .venv/bin/activate
```

If you skipped the install script, install deps now:

```bash
pip install -r requirements.txt
```

Copy the example env file (a working `.env` is already shipped with a generated secret — replace it for production):

```bash
# Linux/RPi
cp .env.example .env
# Windows PowerShell
Copy-Item .env.example .env
```

Then:

```bash
python -m stellegent.cli initdb
python scripts/seed_admin.py             # creates admin/prof/student dev accounts
python scripts/make_sample.py            # writes samples/board.jpg (synthetic test image)
python -m stellegent.cli process samples/board.jpg --course "CS101"
python -m stellegent.cli list
python -m stellegent.cli serve --port 5000
```

The `process` step requires PaddleOCR or EasyOCR installed. If neither is installed yet, skip it and use the web UI's `/upload` after `serve` — the engine loads lazily on first use.

Open `http://localhost:5000`. Login `admin / admin123` (dev only — change `STELLEGENT_JWT_SECRET` in `.env` and reseed users for production).

## Three ways to ingest a board

The capture step is **optional** — anything that produces a whiteboard image can feed the pipeline.

### 1. Web upload (drag-drop, no camera needed)

`/upload` — drag image onto dropzone, or click to browse. Optional course field. POSTs to `/api/upload`, runs the full pipeline (preprocess → OCR → correct → summarize → export → DB), redirects to lecture detail.

- Allowed: `.png .jpg .jpeg .webp .bmp .tif .tiff`
- Max size: 25 MB
- Roles: prof, admin

### 2. Browser live capture (camera attached to RPi, accessed from any device on LAN)

`/live` — MJPEG stream from `/api/stream` with green/orange board outline overlay. Right-side panel polls `/api/guidance` every 500 ms and shows:

- Live messages: "Move left/right", "Step back / Step closer", "Tilt device — reduce skew", "Zoom out / fill frame", "Hold steady — image blurry", "Ready — capture now"
- Stats: sharpness (Laplacian variance), distance (m), skew (°), coverage (0–1)
- Big **Capture** button that turns green when guidance reports `ready`. Click triggers `POST /api/capture` and redirects to lecture detail.

### 3. Native fullscreen UI (RPi 7" touchscreen)

```bash
python -m stellegent.cli capture --pi --fullscreen --course "CS101"
```

OpenCV native window, SPACE = capture, `q` = quit. Same guidance overlay as the web version. Use this when there's no browser, or for kiosk-style operation.

### 4. CLI (offline batch)

```bash
python -m stellegent.cli process samples/board.jpg --course "CS101"
```

## Configuration (env vars / `.env`)

`stellegent/config.py` auto-loads a `.env` file at the repo root. Process env vars override file values.

| Var                     | Default                  | Purpose                                         |
| ----------------------- | ------------------------ | ----------------------------------------------- |
| `STELLEGENT_DATA`       | `./data`                 | output root                                     |
| `STELLEGENT_DB`         | `./stellegent.db`        | SQLite path                                     |
| `STELLEGENT_JWT_SECRET` | (long built-in fallback) | JWT signing key — **must be ≥32 bytes** (PyJWT) |
| `OLLAMA_HOST`           | `http://127.0.0.1:11434` | Ollama API                                      |
| `OLLAMA_MODEL`          | `phi3:mini`              | model tag                                       |

Generate a fresh secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## API

```
POST   /login                                 — body {username,password} -> {token,role}
GET    /api/lectures?date=&course=&q=         — list (auth)
GET    /api/lecture/<id>                       — detail + manifest + annotations
GET    /api/lecture/<id>/file?type=pdf|docx|txt|image|manifest
POST   /api/lecture/<id>/annotate             — body {note}
DELETE /api/lecture/<id>                      — prof/admin
POST   /api/capture                           — prof/admin; single-frame snap from camera + pipeline
POST   /api/upload                            — prof/admin; multipart 'image' + optional 'course'
GET    /api/stream                            — prof/admin; MJPEG live preview w/ overlay
GET    /api/guidance                          — prof/admin; current GuidanceResult JSON
GET    /api/audit                             — admin
```

UI pages: `/` dashboard, `/login`, `/upload`, `/live`, `/lecture/<id>`.

Bearer token via `Authorization: Bearer <jwt>` or `token` cookie. 30-min expiry.

## Pipeline contract

`stellegent.pipeline.process_image(np.ndarray, course_name=None)` runs:

1. `preprocess` — detect corners, rectify, deglare, CLAHE, denoise
2. `run_ocr` — list of `OCRLine(text, confidence, bbox)`
3. `correct_low_confidence` — only lines below 0.75 confidence
4. `summarize` — bullet summary (LLM or LSA fallback)
5. `export_all` — DOCX/PDF/TXT/PNG/JSON manifest under `data/YYYY-MM-DD/<uuid>/`
6. `insert_lecture` — index in SQLite

## Tests

```bash
pip install pytest
pytest tests/
```

Network-/model-free tests for preprocess, guidance, db, export. OCR + NLP tests assume the heavy deps installed.

## Evaluation scripts

```bash
python scripts/eval_wer.py    pred.txt ref.txt   # CRR/WRR
python scripts/eval_rouge.py  pred.txt ref.txt   # ROUGE-1/2/L
python scripts/bench_latency.py samples/board.jpg 5
```

Targets: ≥85% CRR/WRR, ≤30s end-to-end on RPi 5.

## Notes / known constraints

- PaddleOCR ARM wheels are flaky. Code falls back to EasyOCR automatically.
- Phi-3-mini on RPi 5 is the bottleneck. If Ollama is unavailable or slow, `correct_text` falls back to SymSpell and `summarize` falls back to sumy LSA — no network, no model load required.
- `solvePnP`-style distance estimate uses a 66° HFOV assumption (typical RPi camera). Tune in `capture/guidance.py` for your lens.
- DOCX layout heading inference is heuristic (numbered/bulleted regex). Extend with PaddleOCR layout-analysis output for richer structure.
- `/api/stream` opens a single shared `CameraHub`. Flask dev server is single-threaded by default — start with `flask run --with-threads` or `gunicorn -k gthread` if multiple browsers should view the stream simultaneously.
