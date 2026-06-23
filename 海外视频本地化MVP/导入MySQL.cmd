@echo off
chcp 65001 >nul
cd /d "%~dp0"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v OVERSEAS_DB_USERNAME 2^>nul ^| find "OVERSEAS_DB_USERNAME"') do set "OVERSEAS_DB_USERNAME=%%B"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v OVERSEAS_DB_PASSWORD 2^>nul ^| find "OVERSEAS_DB_PASSWORD"') do set "OVERSEAS_DB_PASSWORD=%%B"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v OVERSEAS_DB_URL 2^>nul ^| find "OVERSEAS_DB_URL"') do set "OVERSEAS_DB_URL=%%B"
cd /d "%~dp0.."
call "启动MySQL.cmd" >nul 2>&1
cd /d "%~dp0"
python scripts\pipeline.py db
exit /b %errorlevel%
