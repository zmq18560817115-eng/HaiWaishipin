@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  海外视频本地化工作台
echo  ─────────────────────────────────────
echo  请从本窗口启动，不要用 Cursor 内置终端运行 python。
echo  若 8788 端口已被占用，请先关闭 Cursor 里的旧服务窗口。
echo.

REM TikTok 采集必须能调用本机 Chrome；清除 Cursor 沙箱注入的 Playwright 路径
set PLAYWRIGHT_BROWSERS_PATH=
set WORKBENCH_LAUNCHER=startup-cmd

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 创建工作台 Python 环境...
  python -m venv .venv
)

set "OLM_DIR=%~dp0..\overseas-loc-mvp"
if not exist "%OLM_DIR%\.venv\Scripts\python.exe" (
  echo [2/3] 创建交付引擎 Python 环境（成片拼接 / SeedDance）...
  python -m venv "%OLM_DIR%\.venv"
)

echo [3/3] 安装依赖并启动本地化工作台...
if defined WORKBENCH_HOST (
  echo 打开 http://%WORKBENCH_HOST%:%WORKBENCH_PORT%
) else (
  echo 打开 http://127.0.0.1:8788
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
"%OLM_DIR%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r "%OLM_DIR%\requirements.txt"
".venv\Scripts\python.exe" -m app.main
