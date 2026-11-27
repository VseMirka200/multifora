@echo off
cd /d "%~dp0"
python scripts\install_engines.py wordcraft
if errorlevel 1 (pause & exit /b 1)
python scripts\test_wordcraft.py
pause
