@echo off
REM Local dev launcher (Windows). Runtime state goes under .local\data (NOT
REM .\data, which is the Docker-image default). Builds the SPA, serves on :8000.
setlocal
cd /d "%~dp0"
set "ROOT=%cd%"

REM Config (JWT secret, GEMINI_API_KEY, OLLAMA_*, OCR_BACKEND) is read from .env
REM by the app. These scripts only force runtime state under .local\data.
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo [run] created .env from .env.example - edit it ^(GEMINI_API_KEY / JWT secret^)
)

set "STELLEGENT_DATA=%ROOT%\.local\data"
set "STELLEGENT_DB=%ROOT%\.local\data\stellegent.db"
set "STATIC_DIR=%ROOT%\frontend\build"
if not exist ".local\data" mkdir ".local\data"

set "PY=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [run] creating venv + installing backend...
  python -m venv .venv
  "%PY%" -m pip install -q -e ./backend
)

if not exist "frontend\build\index.html" (
  echo [run] building frontend...
  pushd frontend && call npm ci && call npm run build && popd
)

pushd backend
"%PY%" -m stellegent.cli initdb
"%PY%" scripts\seed_admin.py
echo [run] http://localhost:8000  (admin / admin123)
"%PY%" -m uvicorn stellegent.main:app --host 0.0.0.0 --port 8000
popd

endlocal
