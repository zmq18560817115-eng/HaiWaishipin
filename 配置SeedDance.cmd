@echo off
chcp 65001 >nul
cd /d "%~dp0overseas-loc-mvp"

echo.
echo  SeedDance 2.0 外接配置（fal.ai）
echo  ─────────────────────────────────────
echo  1. 打开 https://fal.ai/dashboard/keys 申请 API Key
echo  2. 在下面打开的 .env 里填写：  FAL_KEY=你的密钥
echo  3. 保存后运行本脚本里的测试
echo.

start notepad ".env"

echo 填好 FAL_KEY 并保存 notepad 后，按任意键测试连接...
pause >nul

".venv\Scripts\python.exe" scripts\test_seedance.py
if errorlevel 1 (
  echo.
  echo 测试失败：请检查 FAL_KEY 是否正确、网络是否可访问 fal.ai
  pause
  exit /b 1
)

echo.
echo 测试成功。请双击「重启出海出稿.cmd」加载新配置。
pause
