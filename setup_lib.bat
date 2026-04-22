@echo off
setlocal enabledelayedexpansion

set "PROJECT=%~dp0"
cd /d "%PROJECT%"

if not exist ".venv" (
    python -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

python -m pip install --upgrade pip
if errorlevel 1 goto :error

python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python -m pip install PyQt6
if errorlevel 1 goto :error

echo Done. Run the project from this same console.
echo .venv is local-only and ignored by Git. Re-run this script on each machine.
pause
exit /b 0

:error
echo Error while installing dependencies.
echo Copy the messages above and send them to me.
pause
exit /b 1
