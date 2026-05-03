# Stellegent

Portable, offline whiteboard-to-document system targeting the Raspberry Pi 5. Captures a classroom whiteboard, preprocesses the image, performs OCR, applies LLM-assisted spelling and grammar correction, generates a summary, exports DOCX, PDF, TXT, PNG, and a JSON manifest, and stores everything in a local SQLite database that is browseable through a Flask web interface.

OCR uses PaddleOCR (PP-OCRv5 mobile). Text correction and summarization use Phi-3-mini served by Ollama.

## Modules

| #   | Module                                             | Path                                          |
| --- | -------------------------------------------------- | --------------------------------------------- |
| 1   | Capture and live preview                           | `stellegent/capture/`                         |
| 2   | Image preprocessing                                | `stellegent/preprocess/`                      |
| 3   | OCR (PaddleOCR PP-OCRv5 mobile)                    | `stellegent/ocr/`                             |
| 4   | Text correction and summarization                  | `stellegent/nlp/`                             |
| 5   | Export (DOCX, PDF, TXT, PNG, JSON)                 | `stellegent/export/`                          |
| 6   | SQLite store                                       | `stellegent/db/`                              |
| 7   | Flask web interface and JWT-authenticated API      | `stellegent/web/`                             |
|     | Pipeline orchestrator and CLI                      | `stellegent/pipeline.py`, `stellegent/cli.py` |

---

## Windows (development)

### 1. Install

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_dev.ps1
.\.venv\Scripts\Activate.ps1
```

If the install script is skipped:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install Ollama from <https://ollama.com/download/windows>, then pull the model.

```powershell
ollama pull phi3:mini
```

### 2. Configure

```powershell
Copy-Item .env.example .env
```

A working `.env` is shipped with a generated 48-byte secret. Replace `STELLEGENT_JWT_SECRET` for production. The JWT key must be at least 32 bytes.

### 3. First run

```powershell
.\.venv\Scripts\Activate.ps1
python -m stellegent.cli initdb
python scripts/seed_admin.py
python -m stellegent.cli serve --port 5000
```

`seed_admin.py` creates `admin`, `prof`, and `student` development accounts. Process a real whiteboard image through the web UI (`/upload` or `/live`) or the CLI:

```powershell
python -m stellegent.cli process path\to\your_image.jpg --course "CS101"
```

Open <http://localhost:5000> and log in as `admin / admin123`. Replace these credentials before deploying.

The first OCR call downloads the PP-OCRv5 mobile weights (approximately 25 MB) into `~/.paddlex/official_models/`.

---

## Raspberry Pi 5 (Bookworm 64-bit, deployment)

### 1. Install

```bash
bash scripts/install_rpi.sh
source .venv/bin/activate
```

The install script performs the following steps:

- installs system packages: `python3-pip python3-venv python3-picamera2 libgl1 libglib2.0-0 sqlite3 build-essential`
- creates a virtual environment and installs `requirements.txt`
- installs Ollama if it is not already present and pulls `phi3:mini`
- runs `python -m stellegent.cli initdb`

ARM64 wheels for `paddlepaddle` are not always available on PyPI. If installation fails on `paddlepaddle`, follow the official ARM build guide at <https://www.paddlepaddle.org.cn/install/>.

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and replace `STELLEGENT_JWT_SECRET` before exposing the service.

### 3. First run

```bash
source .venv/bin/activate
python scripts/seed_admin.py
python -m stellegent.cli serve --host 0.0.0.0 --port 5000
```

To use the native fullscreen capture UI on the 7-inch touchscreen:

```bash
python -m stellegent.cli capture --pi --fullscreen --course "CS101"
```

The web interface is reachable from any device on the local network at `http://<pi-ip>:5000`.

---

## Ingest paths

The capture step is optional. Any whiteboard image can feed the pipeline.

### 1. Web upload

`/upload` provides a drag-and-drop dropzone with optional course tagging. The form posts to `/api/upload`, which runs the full pipeline and redirects to the lecture detail page.

- Accepted extensions: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tif`, `.tiff`
- Maximum file size: 25 MB
- Required role: `prof` or `admin`

### 2. Browser live capture

`/live` shows an MJPEG stream from `/api/stream` with a board-outline overlay. The right-hand panel polls `/api/guidance` every 500 ms and displays:

- Status messages such as "Move left", "Step back", "Tilt device", "Zoom out", "Hold steady", and "Ready"
- Live statistics: sharpness (Laplacian variance), distance in metres, skew in degrees, and frame coverage
- A capture button that turns green when guidance reports `ready`. Clicking it triggers `POST /api/capture` and redirects to the lecture detail page.

### 3. Native fullscreen UI

```bash
python -m stellegent.cli capture --pi --fullscreen --course "CS101"
```

OpenCV native window. SPACE captures, `q` quits. Same overlay as the browser version. Suitable for kiosk use.

### 4. Command-line batch

```bash
python -m stellegent.cli process path/to/your_image.jpg --course "CS101"
```

---

## Configuration

`stellegent/config.py` automatically loads a `.env` file at the repository root. Process environment variables override file values. Relative paths in `STELLEGENT_DATA` and `STELLEGENT_DB` are resolved against the repository root.

| Variable                | Default                  | Purpose                                       |
| ----------------------- | ------------------------ | --------------------------------------------- |
| `STELLEGENT_DATA`       | `./data`                 | Output root for capture artefacts             |
| `STELLEGENT_DB`         | `./stellegent.db`        | SQLite database path                          |
| `STELLEGENT_JWT_SECRET` | built-in 48-byte default | JWT signing key. Must be at least 32 bytes.   |
| `OLLAMA_HOST`           | `http://127.0.0.1:11434` | Ollama HTTP endpoint                          |
| `OLLAMA_MODEL`          | `phi3:mini`              | Ollama model tag                              |

To generate a fresh secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## API

```
POST   /login                                  body {username,password} -> {token,role}
GET    /api/lectures?date=&course=&q=          list lectures
GET    /api/lecture/<id>                       lecture detail, manifest, annotations
GET    /api/lecture/<id>/file?type=pdf|docx|txt|image|manifest
POST   /api/lecture/<id>/annotate              body {note}
DELETE /api/lecture/<id>                       prof or admin
POST   /api/capture                            prof or admin: single-frame snap and pipeline
POST   /api/upload                             prof or admin: multipart 'image' and optional 'course'
GET    /api/stream                             prof or admin: MJPEG live preview with overlay
GET    /api/guidance                           prof or admin: current GuidanceResult JSON
GET    /api/audit                              admin
```

UI pages: `/`, `/login`, `/upload`, `/live`, `/lecture/<id>`.

Authentication uses `Authorization: Bearer <jwt>` or a `token` cookie. Tokens expire after 30 minutes.

---

## Pipeline contract

`stellegent.pipeline.process_image(image, course_name=None)` runs:

1. `preprocess` detects board corners, rectifies the perspective, removes specular glare, applies CLAHE, and denoises.
2. `run_ocr` returns a list of `OCRLine(text, confidence, bbox)` from PaddleOCR PP-OCRv5 mobile.
3. `correct_low_confidence` rewrites only lines whose confidence is below 0.75.
4. `summarize` produces a bullet-point summary using the local LLM.
5. `export_all` writes DOCX, PDF, TXT, PNG, and a JSON manifest under `data/YYYY-MM-DD/<uuid>/`.
6. `insert_lecture` indexes the result in SQLite.

---

## Tests

```bash
pip install pytest
pytest tests/
```

The included tests for preprocessing, guidance, the database, and export do not require network access or model weights. OCR and NLP tests require the full dependency set.

---

## Evaluation scripts

```bash
python scripts/eval_wer.py pred.txt ref.txt
python scripts/eval_rouge.py pred.txt ref.txt
python scripts/bench_latency.py path/to/your_image.jpg 5
```

Targets: at least 85 percent character and word recognition rate, and end-to-end processing under 30 seconds on the Raspberry Pi 5.

---

## Known constraints

- OCR engine: PaddleOCR `>=3.0` with the PP-OCRv5 mobile build. ARM wheels: <https://www.paddlepaddle.org.cn/install/>.
- NumPy is pinned to `<2` because `paddlex` and `skimage` are compiled against the 1.x ABI.
- `opencv-python` and `opencv-python-headless` are pinned to `<4.11` because newer releases require NumPy `>=2`. PaddleOCR pulls `opencv-python-headless` transitively, so both packages are pinned.
- On Windows with a CPU build of `paddlepaddle 3.3.x`, MKL-DNN raises `ConvertPirAttribute2RuntimeAttribute`. The engine sets `enable_mkldnn=False` to work around this.
- Phi-3-mini on the Raspberry Pi 5 is the slowest stage. Expect several seconds per call on 8 GB RAM; pre-pull the model with `ollama pull phi3:mini` so it is warm in memory.
- The distance estimate uses a 66-degree horizontal field of view typical of the Raspberry Pi camera. Adjust in `capture/guidance.py` for other lenses.
- DOCX heading inference is heuristic and based on regular expressions. Replace with PaddleOCR layout analysis output for richer structure.
- `/api/stream` opens a single shared `CameraHub`. The Flask development server is single-threaded by default. Run with `flask run --with-threads` or `gunicorn -k gthread` to allow multiple concurrent stream viewers.
