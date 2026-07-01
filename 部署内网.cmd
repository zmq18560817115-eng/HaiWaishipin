@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  海外视频本地化 · 内网部署启动
echo  ─────────────────────────────────────
echo.

if not exist "海外视频本地化MVP\.venv\Scripts\python.exe" (
  echo 请先运行「检查开发环境.cmd」
  pause
  exit /b 1
)

if not exist "海外视频本地化MVP\.env" (
  echo 首次部署：从 .env.example 复制配置…
  copy /Y "海外视频本地化MVP\.env.example" "海外视频本地化MVP\.env" >nul
)

REM 内网默认监听所有网卡（可在 海外视频本地化MVP\.env 覆盖）
set WORKBENCH_HOST=0.0.0.0
set WORKBENCH_PORT=8788

echo  监听 %WORKBENCH_HOST%:%WORKBENCH_PORT%
echo  请在 海外视频本地化MVP\.env 中设置 WORKBENCH_API_TOKEN（建议）
echo  成片：用户页面下载 zip + 服务器 03_产出库 自动归档
echo  备份：运行「备份工作区.cmd」或设置页「立即备份工作区」
echo.

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  set _IP=%%a
  goto :gotip
)
:gotip
if defined _IP echo  局域网访问示例：http://%_IP: =%:%WORKBENCH_PORT%
echo.

start "本地化工作台-内网" cmd /k "cd /d "%~dp0海外视频本地化MVP" && set WORKBENCH_HOST=0.0.0.0 && call 启动页面.cmd"
timeout /t 3 /nobreak >nul
echo  服务窗口已打开，请勿关闭。
pause
