@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PRODUCT_ID=便携恒温杯"
if not "%~1"=="" set "PRODUCT_ID=%~1"
if exist .venv\Scripts\python.exe (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)
echo.
echo  素材库整理 — 品类: %PRODUCT_ID%
echo  ─────────────────────────────────────
echo  1/2 预览...
"%PY%" scripts\pipeline.py prune --dry-run --product-id "%PRODUCT_ID%"
if errorlevel 1 goto :err
echo.
set /p CONFIRM=确认执行清理？输入 Y 继续:
if /i not "%CONFIRM%"=="Y" goto :eof
echo  2/2 执行...
"%PY%" scripts\pipeline.py prune --product-id "%PRODUCT_ID%"
if errorlevel 1 goto :err
echo.
echo  完成。请刷新工作台查看素材数量。
goto :eof
:err
echo  失败，请查看上方输出。
pause
exit /b 1
