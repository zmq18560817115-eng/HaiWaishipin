@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo.
echo  检查 / 初始化开发环境
echo  -------------------------------------
echo  · 双 venv（8788 工作台 + 交付引擎）
echo  · MySQL 3306（可选）
echo  · 8788 健康检查
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-dev-env.ps1"
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo  请先安装 Python 3.12，或双击「启动工作台.cmd」首次创建 venv。
)
pause
exit /b %ERR%
