@echo off
setlocal
cd /d "%~dp0"

set "SLUG=%~1"
if "%SLUG%"=="" (
  echo 用法: 归档MVP产出.cmd ^<slug^>
  echo 示例: 归档MVP产出.cmd night-pumping-v1
  echo       归档MVP产出.cmd flange-size-v1
  exit /b 1
)

if not exist "overseas-loc-mvp\.venv\Scripts\python.exe" (
  echo 未找到 Python 环境，请先运行 启动页面MVP.cmd 完成依赖安装。
  exit /b 1
)

"overseas-loc-mvp\.venv\Scripts\python.exe" "overseas-loc-mvp\scripts\archive_run.py" %SLUG%
exit /b %ERRORLEVEL%
