@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  海外视频本地化工作台
echo  -------------------------------------
echo  请从本窗口启动，不要用 Cursor 内置终端运行 python。
echo  若 8788 端口已被占用，请先关闭 Cursor 里的旧服务窗口。
echo.

REM TikTok 采集必须能调用本机 Chrome；清除 Cursor 沙箱注入的 Playwright 路径
set PLAYWRIGHT_BROWSERS_PATH=
set WORKBENCH_LAUNCHER=startup-cmd

".venv\Scripts\python.exe" -c "import sys" 2>nul
if errorlevel 1 (
  if exist ".venv" (
    echo [修复] 工作台 venv 损坏，正在重建...
    rmdir /s /q ".venv"
  )
  echo [1/3] 创建工作台 Python 环境...
  python -m venv .venv
)

set "OLM_DIR=%~dp0..\overseas-loc-mvp"
"%OLM_DIR%\.venv\Scripts\python.exe" -c "import sys" 2>nul
if errorlevel 1 (
  if exist "%OLM_DIR%\.venv" (
    echo [修复] 交付引擎 venv 损坏，正在重建...
    rmdir /s /q "%OLM_DIR%\.venv"
  )
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
"%OLM_DIR%\.venv\Scripts\python.exe" -c "import imageio_ffmpeg; p=imageio_ffmpeg.get_ffmpeg_exe(); assert p, 'ffmpeg missing'" 2>nul
if errorlevel 1 (
  echo [警告] 交付引擎 ffmpeg 未就绪，正在单独安装 imageio-ffmpeg...
  "%OLM_DIR%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check imageio-ffmpeg
)
".venv\Scripts\python.exe" -m app.main
