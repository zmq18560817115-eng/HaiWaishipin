@echo off
setlocal

set "MYSQLADMIN=%LOCALAPPDATA%\Programs\DevTools\mysql\PFiles64\MySQL\MySQL Server 8.4\bin\mysqladmin.exe"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v MYSQL_ROOT_PASSWORD 2^>nul ^| find "MYSQL_ROOT_PASSWORD"') do set "MYSQL_ROOT_PASSWORD=%%B"

"%MYSQLADMIN%" --no-defaults --host=127.0.0.1 --port=3306 --protocol=TCP --user=root --password="%MYSQL_ROOT_PASSWORD%" shutdown 2>nul
if %errorlevel% equ 0 (
  echo MySQL stopped.
  exit /b 0
)

echo MySQL is not running, or the user environment is unavailable.
exit /b 1
