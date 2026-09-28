@echo off
setlocal EnableExtensions

set "PROJECT=%~dp0.."
set "ISCC_EXE="
cd /d "%PROJECT%"

if /i "%~1"=="--skip-app-build" goto app_ready
if not "%~1"=="" goto usage

call "scripts\build_app.bat" --no-pause
if errorlevel 1 goto error

:app_ready
if not exist "dist\Multifora\Multifora.exe" (
    echo ERROR: dist\Multifora\Multifora.exe was not found.
    echo Run this script without --skip-app-build to build the application first.
    goto error
)

if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC_EXE set "ISCC_EXE=%%I"

if not defined ISCC_EXE (
    echo ERROR: Inno Setup 6 was not found.
    echo Download it from https://jrsoftware.org/isdl.php and run this script again.
    goto error
)

set "APP_VERSION="
for /f "tokens=3" %%V in ('findstr /b /c:"APP_VERSION = " "app\core\app_identity.py"') do set "APP_VERSION=%%~V"
if not defined APP_VERSION (
    echo ERROR: Could not read APP_VERSION from app\core\app_identity.py.
    goto error
)

echo Building installer for Multifora %APP_VERSION%...
"%ISCC_EXE%" /Qp "/DMyAppVersion=%APP_VERSION%" "scripts\installer.iss"
if errorlevel 1 goto error

echo Installer created: dist\installer\Multifora-Setup-%APP_VERSION%.exe
exit /b 0

:usage
echo Usage: %~nx0 [--skip-app-build]
exit /b 2

:error
echo Installer build failed.
exit /b 1
