# Stellegent

Portable, offline whiteboard-to-document system. RPi 5 target. Captures classroom whiteboard, preprocesses, OCRs, corrects + summarizes via local LLM, exports DOCX/PDF/TXT, stores in SQLite, browses via Flask web UI.

## Modules

| #   | Module                                             | Path                                          |
| --- | -------------------------------------------------- | --------------------------------------------- |
| 1   | Capture + live preview                             | `stellegent/capture/`                         |
| 2   | Preprocessing                                      | `stellegent/preprocess/`                      |
| 3   | OCR (PaddleOCR v5 / PP-OCRv5 mobile)               | `stellegent/ocr/`                             |
| 4   | NLP correct + summarize (Ollama / SymSpell + sumy) | `stellegent/nlp/`                             |
| 5   | Export DOCX/PDF/TXT/JSON                           | `stellegent/export/`                          |
| 6   | SQLite store                                       | `stellegent/db/`                              |
| 7   | Flask web + JWT auth                               | `stellegent/web/`                             |
| —   | Orchestrator + CLI                                 | `stellegent/pipeline.py`, `stellegent/cli.py` |

PaddleOCR (PP-OCRv5 mobile) is the only OCR engine. LLM is Phi-3-mini via Ollama.

---

## Windows (development)

### 1. Install

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_dev.ps1
.\.venv\Scripts\Activate.ps1
```

If you skipped the install script:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optional — install Ollama + pull the model for LLM correction/summarization (otherwise SymSpell + sumy LSA fallbacks are used automatically):

```powershell
# Install from https://ollama.com/download/windows, then:
ollama pull phi3:mini
```

### 2. Configure

```powershell
Copy-Item .env.example .env
# Edit .env if you want to change paths or rotate the JWT secret.
# A working .env with a generated 48-byte secret is already shipped — replace it for production.
```

### 3. First run

```powershell
.\.venv\Scripts\Activate.ps1
python -m stellegent.cli initdb
python scripts/seed_admin.py             # creates admin / prof / student dev accounts
python scripts/make_sample.py            # writes samples/board.jpg (synthetic test image)
python -m stellegent.cli process samples/board.jpg --course "CS101"
python -m stellegent.cli list
python -m stellegent.cli serve --port 5000
```

Open `http://localhost:5000`. Login `admin / admin123` (dev only — change `STELLEGENT_JWT_SECRET` in `.env` and reseed users for production).

> First OCR call downloads the PP-OCRv5 mobile weights (~25 MB) into `~/.paddlex/official_models/`.
> Windows + CPU has a known MKL-DNN bug in `paddlepaddle 3.3.x`; the engine sets `enable_mkldnn=False` automatically.

---

## 🥧 Raspberry Pi 5 (Bookworm 64-bit, deployment)

### 1. Install

```bash
bash scripts/install_rpi.sh
source .venv/bin/activate
```

`install_rpi.sh` does the following:

- `apt install` of `python3-pip python3-venv python3-picamera2 libgl1 libglib2.0-0 sqlite3 build-essential`
- creates `.venv` and installs `requirements.txt`
- installs Ollama (skipped if already present) and pulls `phi3:mini`
- runs `python -m stellegent.cli initdb`

ARM64 wheels for `paddlepaddle` are not always on PyPI. If the install fails on `paddlepaddle`, follow the official ARM build guide: <https://www.paddlepaddle.org.cn/install/>.

### 2. Configure

```bash
cp .env.example .env
# Edit .env — at minimum, replace STELLEGENT_JWT_SECRET for production.
```

### 3. First run

```bash
source .venv/bin/activate
python scripts/seed_admin.py             # creates admin / prof / student dev accounts
python -m stellegent.cli serve --host 0.0.0.0 --port 5000
```

For live capture on the 7" touchscreen (no browser needed):

```bash
python -m stellegent.cli capture --pi --fullscreen --course "CS101"
```

Access the web UI from any device on the LAN at `http://<pi-ip>:5000`. Login `admin / admin123`.

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

- PaddleOCR is the only OCR engine (PP-OCRv5 mobile build, `paddleocr>=3.0`). No fallback engine — if init fails, fix the install. ARM wheels: https://www.paddlepaddle.org.cn/install/.
- `numpy<2` is required (skimage / paddlex compiled against the 1.x ABI). Already pinned in `requirements.txt`.
- `opencv-python` and `opencv-python-headless` are pinned to `<4.11`. Versions 4.11+ require numpy ≥2 and conflict with the constraint above. PaddleOCR pulls in `opencv-python-headless` transitively, so both are pinned.
- On Windows + CPU, MKL-DNN in paddlepaddle 3.3.x throws `ConvertPirAttribute2RuntimeAttribute` errors. The engine sets `enable_mkldnn=False` to work around this — leave it disabled unless you've upgraded.
- `make_sample.py` writes a _synthetic_ board for smoke-testing OCR alone, not the full preprocessing pipeline. Real whiteboard photos work normally; the synthetic image's perfect rectangle interacts badly with CLAHE/glare-inpaint. To verify OCR on the synthetic image, call `stellegent.ocr.run_ocr(cv2.imread('samples/board.jpg'))` directly.
- Phi-3-mini on RPi 5 is the bottleneck. If Ollama is unavailable or slow, `correct_text` falls back to SymSpell and `summarize` falls back to sumy LSA — no network, no model load required.
- `solvePnP`-style distance estimate uses a 66° HFOV assumption (typical RPi camera). Tune in `capture/guidance.py` for your lens.
- DOCX layout heading inference is heuristic (numbered/bulleted regex). Extend with PaddleOCR layout-analysis output for richer structure.
- `/api/stream` opens a single shared `CameraHub`. Flask dev server is single-threaded by default — start with `flask run --with-threads` or `gunicorn -k gthread` if multiple browsers should view the stream simultaneously.
