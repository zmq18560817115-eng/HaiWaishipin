@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo 正在创建 Python 虚拟环境...
  python -m venv .venv
)

echo 安装 Playwright Chromium 浏览器（TikTok 采集需要）...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q playwright
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 (
  echo.
  echo [跳过] Playwright 浏览器包下载失败（多为网络/CDN 问题）。
  echo 若本机已安装 Google Chrome 或 Edge，可直接关闭本窗口，
  echo 用「启动页面.cmd」打开工作台后重试 TikTok 采集（会自动调用本机浏览器）。
  pause
  exit /b 0
)

echo.
echo 完成。请重新打开工作台后再试 TikTok 采集。
pause
