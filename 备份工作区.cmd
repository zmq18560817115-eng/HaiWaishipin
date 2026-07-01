@echo off
chcp 65001 >nul
cd /d "%~dp0海外视频本地化MVP"

echo.
echo  备份工作区（01素材库 / 03产出库 / 04成稿 / 05反馈 / runs）
echo  ─────────────────────────────────────
echo.

if not exist ".venv\Scripts\python.exe" (
  echo 未找到 .venv，请先运行「检查开发环境.cmd」
  pause
  exit /b 1
)

".venv\Scripts\python.exe" scripts\backup_workspace.py
set ERR=%ERRORLEVEL%
echo.
if %ERR% equ 0 (
  echo  备份完成。默认目录：06_备份库\
) else (
  echo  备份未完全成功，请查看上方输出。
)
pause
exit /b %ERR%
