@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-dev-env.ps1"
exit /b %ERRORLEVEL%
