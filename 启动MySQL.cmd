@echo off
setlocal

set "MYSQLD=%LOCALAPPDATA%\Programs\DevTools\mysql\PFiles64\MySQL\MySQL Server 8.4\bin\mysqld.exe"
set "MYSQL_CONFIG=%LOCALAPPDATA%\Programs\DevTools\mysql\my.ini"

powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if %errorlevel% equ 0 (
  echo MySQL is already running at 127.0.0.1:3306
  exit /b 0
)

powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '%MYSQLD%' -ArgumentList '--defaults-file=%MYSQL_CONFIG%' -WindowStyle Hidden"

for /l %%i in (1,1,30) do (
  powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
  if not errorlevel 1 (
    echo MySQL started at 127.0.0.1:3306
    exit /b 0
  )
  powershell -NoProfile -Command "Start-Sleep -Seconds 1"
)

echo MySQL failed to start. Check:
echo %LOCALAPPDATA%\OverseasVideoLoc\mysql-error.log
exit /b 1
