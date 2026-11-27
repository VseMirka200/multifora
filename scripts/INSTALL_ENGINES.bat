@echo off
cd /d "%~dp0"
python scripts\install_engines.py %*
if errorlevel 1 (echo Engine download failed. & pause & exit /b 1)
echo Engines installed.
pause
