@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
  echo.
  echo  TikTok 竞品流水线
  echo  ─────────────────────────────────────
  echo   links      生成 50 条链接表
  echo   fetch      抓取视频信息
  echo   db         导入 MySQL（可选）
  echo   decompose  单条 AI 拆解 → video_analysis
  echo   templates  爆款结构模板库
  echo   products   产品资料库 ^(DS223^)
  echo   knowledge  知识库检索 ^(KRO^)
  echo   bridge     对接到 MVP 页面
  echo.
  echo  示例: 运行.cmd fetch
  echo        运行.cmd bridge --id 19
  echo.
  goto :eof
)
if "%~1"=="db" (
  cd /d "%~dp0.."
  for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v OVERSEAS_DB_USERNAME 2^>nul ^| find "OVERSEAS_DB_USERNAME"') do set "OVERSEAS_DB_USERNAME=%%B"
  for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v OVERSEAS_DB_PASSWORD 2^>nul ^| find "OVERSEAS_DB_PASSWORD"') do set "OVERSEAS_DB_PASSWORD=%%B"
  call "启动MySQL.cmd" >nul 2>&1
  cd /d "%~dp0"
)
python scripts\pipeline.py %*
