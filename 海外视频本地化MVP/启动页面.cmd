@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] 创建 Python 环境...
  python -m venv .venv
)

echo [2/2] 启动本地化工作台...
echo 打开 http://127.0.0.1:8788
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
".venv\Scripts\python.exe" -m app.main
