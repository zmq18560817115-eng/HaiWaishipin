@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  海外视频本地化工作台
echo  ─────────────────────────────────────
echo  请从本窗口启动，不要用 Cursor 内置终端运行 python。
echo  若 8788 端口已被占用，请先关闭 Cursor 里的旧服务窗口。
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] 创建 Python 环境...
  python -m venv .venv
)

echo [2/2] 启动本地化工作台...
if defined WORKBENCH_HOST (
  echo 打开 http://%WORKBENCH_HOST%:%WORKBENCH_PORT%
) else (
  echo 打开 http://127.0.0.1:8788
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
".venv\Scripts\python.exe" -m app.main
