@echo off
setlocal enabledelayedexpansion

set "PROJECT=%~dp0"
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
if exist "dist\Multifora" rmdir /s /q "dist\Multifora"

python -m PyInstaller --noconfirm --clean --windowed --name Multifora --icon "icons\icon.ico" multifora_start.pyw
if errorlevel 1 goto :error

if exist "icons" (
    robocopy "icons" "dist\Multifora\icons" /E /NFL /NDL /NJH /NJS /NP >nul
)
if exist "materials" (
    robocopy "materials" "dist\Multifora\materials" /E /NFL /NDL /NJH /NJS /NP >nul
)
if exist "bin" (
    robocopy "bin" "dist\Multifora\bin" /E /NFL /NDL /NJH /NJS /NP >nul
)

echo Build complete. Output: dist\Multifora
pause
exit /b 0

:error
echo Build failed.
pause
exit /b 1
