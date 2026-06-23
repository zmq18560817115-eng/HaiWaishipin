@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  海外视频本地化工作台 · 一键启动
echo  ─────────────────────────────────────
echo  打开 http://127.0.0.1:8788
echo  素材库 → 脚本生成 → 成稿库 → 反馈库
echo  脚本生成页可「完成交付」并下载 zip（无需再开 8787）
echo.

start "" "http://127.0.0.1:8788"

powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8788/api/health' -UseBasicParsing -TimeoutSec 2).StatusCode } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  start "本地化工作台" cmd /k "cd /d "%~dp0海外视频本地化MVP" && call 启动页面.cmd"
  timeout /t 4 /nobreak >nul
)

echo  浏览器已打开工作台。首次使用请到「设置」同步 TikTok。
pause
