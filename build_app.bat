@echo off
setlocal enabledelayedexpansion

set "PROJECT=%~dp0"
set "APP_BUILD_NAME=Multifora"
cd /d "%PROJECT%"

if not exist ".venv" (
    call "setup_lib.bat"
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

python -m pip install pyinstaller
if errorlevel 1 goto :error

if exist "build" rmdir /s /q "build"
if exist "dist\%APP_BUILD_NAME%" rmdir /s /q "dist\%APP_BUILD_NAME%"

python -m PyInstaller --noconfirm --clean --windowed --name "%APP_BUILD_NAME%" --icon "icons\icon.ico" multifora_start.pyw
if errorlevel 1 goto :error

if exist "icons" (
    robocopy "icons" "dist\%APP_BUILD_NAME%\icons" /E /NFL /NDL /NJH /NJS /NP >nul
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
