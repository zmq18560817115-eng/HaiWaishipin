@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating local Python environment...
  python -m venv .venv
)

echo [2/3] Checking dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt

echo [2.5/3] Stopping previous server on port 8787...
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue; if ($c) { $c | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }"
timeout /t 1 /nobreak >nul

echo [2.6/3] Upgrading delivery files...
".venv\Scripts\python.exe" scripts\regen_delivery.py >nul 2>&1

echo [3/3] Starting Overseas Video Localization MVP...
echo Open http://127.0.0.1:8787
".venv\Scripts\python.exe" -m app.main

endlocal

