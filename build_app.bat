@echo off
setlocal enabledelayedexpansion

set "PROJECT=%~dp0"
set "APP_BUILD_NAME=Multifora"
cd /d "%PROJECT%"

if not exist ".venv\Scripts\python.exe" (
    where py.exe >nul 2>nul
    if not errorlevel 1 (
        py.exe -3 -m venv ".venv"
    ) else (
        python -m venv ".venv"
    )
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

python -m pip install -r "requirements.txt"
if errorlevel 1 goto :error
python -m pip install "PyInstaller>=6.0.0,<7"
if errorlevel 1 goto :error

if exist "build" rmdir /s /q "build"
if exist "dist\%APP_BUILD_NAME%" rmdir /s /q "dist\%APP_BUILD_NAME%"

python -m PyInstaller --noconfirm --clean --windowed --name "%APP_BUILD_NAME%" --icon "assets\icon.ico" --add-data "assets;assets" multifora_start.py
if errorlevel 1 goto :error

if exist "assets" (
    robocopy "assets" "dist\%APP_BUILD_NAME%\assets" /E /NFL /NDL /NJH /NJS /NP >nul
)
if exist "bin" (
    robocopy "bin" "dist\%APP_BUILD_NAME%\bin" /E /NFL /NDL /NJH /NJS /NP >nul
)

echo Build complete. Output: dist\%APP_BUILD_NAME%
pause
exit /b 0

:error
echo Build failed.
pause
exit /b 1
