@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  检查 DS223 是否在线...
if exist "\\DS223\obsidian知识库\" (
  echo  [OK] DS223 可访问
) else (
  echo  [!!] DS223 离线 — 请先连公司内网/VPN，再重新运行本脚本
  echo.
)
echo.
call 运行.cmd products
echo.
call 运行.cmd knowledge
echo.
pause
