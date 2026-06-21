@echo off
setlocal

REM Windows development launcher only.
REM Browser-facing dev app runs on :8000, matching production.
REM FastAPI runs on :8001 with reload; Vite proxies /api to it.
REM This script never builds or serves the production SPA.

cd /d "%~dp0"
set "ROOT=%cd%"

echo [run] Stellegent dev mode (LAN-exposed on 0.0.0.0)
echo [run] Open app:    http://127.0.0.1:8000
echo [run] Backend API: http://127.0.0.1:8001
echo [run] LAN access:  http://^<this-PC-LAN-IP^>:8000  (run "ipconfig" to find it)
echo.

if not exist ".env" (
  if not exist ".env.example" (
    echo [run] missing .env and .env.example
    goto fail
  )
  copy ".env.example" ".env" >nul
  echo [run] created .env from .env.example - edit GEMINI_API_KEY / JWT secret as needed
)

REM Keep all local runtime state in the default gitignored data/ path.
set "CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000"
set "STELLEGENT_DEV_API_TARGET=http://127.0.0.1:8001"

REM Force dev-only behavior even if frontend\build exists from an old build.
set "STATIC_DIR=%TEMP%\stellegent-dev-static-disabled-%RANDOM%-%RANDOM%"

if not exist "data" mkdir "data"

set "PY=%ROOT%\.venv\Scripts\python.exe"
set "DEV_MARKER=%ROOT%\.venv\.stellegent-dev-installed"
if not exist "%PY%" (
  echo [run] creating Python venv...
  python -m venv .venv
  if errorlevel 1 goto fail
)

if not exist "%DEV_MARKER%" (
  echo [run] installing backend in editable dev mode...
  "%PY%" -m pip install -q -e "./backend[dev]"
  if errorlevel 1 goto fail
  type nul > "%DEV_MARKER%"
)

if not exist "frontend\node_modules" (
  echo [run] installing frontend dependencies...
  pushd frontend
  call npm install
  if errorlevel 1 (
    popd
    goto fail
  )
  popd
)

echo [run] initializing dev database...
pushd backend
"%PY%" -m stellegent.cli initdb
if errorlevel 1 (
  popd
  goto fail
)
popd

REM Free the dev ports. Leftover backend/vite from a previous run keeps
REM listening, and vite dev uses --strictPort, so a stale process on :8000
REM crashes the frontend with "Port 8000 is already in use".
call :freeport 8000
call :freeport 8001

echo.
echo [run] Starting FastAPI with reload in a new window.
echo [run] Starting Vite on the production-like app port in this window.
echo [run] Dev users: admin/admin123, prof/prof123, student/student123
echo.

start "Stellegent API dev" /D "%ROOT%\backend" cmd /k ""%PY%" -m stellegent.cli serve --host 0.0.0.0 --port 8001 --reload"

pushd frontend
call npm run dev -- --host 0.0.0.0 --port 8000 --strictPort
set "FRONTEND_EXIT=%ERRORLEVEL%"
popd

exit /b %FRONTEND_EXIT%

REM Kill any process listening on the given port (dev launcher owns :8000/:8001).
:freeport
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%~1 " ^| findstr LISTENING') do (
  echo [run] freeing port %~1 (killing PID %%p)
  taskkill /F /PID %%p >nul 2>&1
)
goto :eof

:fail
echo.
echo [run] dev startup failed.
exit /b 1
