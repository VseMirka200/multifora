@echo off
setlocal enabledelayedexpansion

set "PROJECT=%~dp0.."
set "APP_BUILD_NAME=Multifora"
cd /d "%PROJECT%"

rem Use the selected Python when supported; otherwise try the 3.11 launcher.
set "BUILD_PYTHON=python"
python "scripts\verify_build_environment.py" --python-only >nul 2>nul
if errorlevel 1 set "BUILD_PYTHON=py.exe -3.11"
%BUILD_PYTHON% "scripts\verify_build_environment.py" --python-only
if errorlevel 1 goto :error

if not exist ".venv-build\Scripts\python.exe" (
    %BUILD_PYTHON% -m venv ".venv-build"
    if errorlevel 1 goto :error
)

set BUILD_PYTHON="%PROJECT%\.venv-build\Scripts\python.exe"
%BUILD_PYTHON% "scripts\verify_build_environment.py" --python-only
if errorlevel 1 goto :error

%BUILD_PYTHON% -m pip install -r "requirements-build.txt"
if errorlevel 1 goto :error
%BUILD_PYTHON% -m pip check
if errorlevel 1 goto :error
%BUILD_PYTHON% "scripts\verify_build_environment.py"
if errorlevel 1 goto :error

if exist "build" rmdir /s /q "build"
if exist "dist\%APP_BUILD_NAME%" rmdir /s /q "dist\%APP_BUILD_NAME%"

%BUILD_PYTHON% -m PyInstaller --noconfirm --clean "Multifora.spec"
if errorlevel 1 goto :error

if not exist "dist\%APP_BUILD_NAME%\%APP_BUILD_NAME%.exe" goto :error

if exist "bin" (
    robocopy "bin" "dist\%APP_BUILD_NAME%\bin" /E /NFL /NDL /NJH /NJS /NP >nul
    if errorlevel 8 goto :error
)

%BUILD_PYTHON% "scripts\verify_windows_bundle.py" --bundle "dist\%APP_BUILD_NAME%"
if errorlevel 1 goto :error

echo Build complete. Output: dist\%APP_BUILD_NAME%
if /i not "%~1"=="--no-pause" pause
exit /b 0

:error
echo Build failed.
if /i not "%~1"=="--no-pause" pause
exit /b 1
