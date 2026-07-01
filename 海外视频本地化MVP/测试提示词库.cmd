@echo off
chcp 65001 >nul
cd /d "%~dp0"
python scripts\test_prompt_library.py
pause
