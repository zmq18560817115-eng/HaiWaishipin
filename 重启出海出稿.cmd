@echo off
chcp 65001 >nul
set "ROOT=%~dp0overseas-loc-mvp"
cd /d "%ROOT%"

echo [1/4] Stop old server on 8787...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8787" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/4] Upgrade delivery files...
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\regen_delivery.py
) else (
  echo WARN: venv missing, skip regen
)

echo [3/4] Start server...
start "出海出稿-8787" cmd /k "cd /d \"%ROOT%\" && call start.bat"

echo [4/4] Wait and open browser...
timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:8787/?ref=ref-001"

echo.
echo Done. Zip: 交付脚本包.md/json + subtitles.srt + 剪辑单.html
if /i not "%~1"=="silent" pause
