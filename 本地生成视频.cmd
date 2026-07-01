@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  本地生成视频（不依赖 8788 页面，直接调 SeedDance）
echo  ────────────────────────────────────────────────────
echo  用法: 本地生成视频.cmd 23
echo        本地生成视频.cmd ref-023
echo  成片复制到: %~dp003_产出库\{项目}\{时间戳}\final-video.mp4
echo.

set "ARG=%~1"
if "%ARG%"=="" (
  echo [提示] 未指定项目编号，默认 ref-023（对标 #23）
  set "ARG=23"
)

cd /d "%~dp0overseas-loc-mvp"
if not exist ".venv\Scripts\python.exe" (
  echo [失败] 未找到 overseas-loc-mvp\.venv，请先运行「检查开发环境.cmd」
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -u scripts\run_seedance_assemble.py %ARG%
set ERR=%ERRORLEVEL%

cd /d "%~dp0"
if exist "%~dp003_产出库\ref-*" (
  for /f "delims=" %%D in ('dir /b /ad /o-d "%~dp003_产出库\ref-*" 2^>nul') do (
    for /f "delims=" %%V in ('dir /b /ad /o-d "%~dp003_产出库\%%D" 2^>nul') do (
      if exist "%~dp003_产出库\%%D\%%V\final-video.mp4" (
        echo.
        echo 打开最新成片: %~dp003_产出库\%%D\%%V\final-video.mp4
        start "" "%~dp003_产出库\%%D\%%V\final-video.mp4"
        goto :done
      )
    )
  )
)
:done
pause
exit /b %ERR%
