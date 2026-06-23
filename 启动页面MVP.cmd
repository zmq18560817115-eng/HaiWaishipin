@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 已合并至「启动工作台.cmd」，正在转发…
call "%~dp0启动工作台.cmd"
