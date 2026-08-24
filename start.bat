@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Multifora

set "APP_ENTRY=multifora_start.py"
set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "PYTHON_EXE="
set "PYTHON_ARGS="

if not exist "%APP_ENTRY%" (
    echo.
    echo ERROR: %APP_ENTRY% was not found.
    echo Keep start.bat in the project root directory.
    goto error
)

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 goto venv_ready

    echo Removing an incompatible virtual environment...
    rmdir /s /q "%VENV_DIR%"
)

where py.exe >nul 2>nul
if not errorlevel 1 (
    py.exe -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=py.exe"
        set "PYTHON_ARGS=-3"
        goto python_found
    )
)

for /f "delims=" %%D in ('dir /b /ad /o-n "%LocalAppData%\Programs\Python\Python3*" 2^>nul') do (
    if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\%%D\python.exe" (
        "%LocalAppData%\Programs\Python\%%D\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
        if not errorlevel 1 set "PYTHON_EXE=%LocalAppData%\Programs\Python\%%D\python.exe"
    )
)
if defined PYTHON_EXE goto python_found

where python.exe >nul 2>nul
if not errorlevel 1 (
    python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=python.exe"
        goto python_found
    )
)

echo.
echo ERROR: Python 3.11 or newer was not found.
echo Download: https://www.python.org/downloads/
goto error

:python_found
echo Creating virtual environment...
"%PYTHON_EXE%" %PYTHON_ARGS% -m venv "%VENV_DIR%"
if errorlevel 1 goto error

:venv_ready
set "PYTHONNOUSERSITE=1"

echo Checking required packages...
"%VENV_PY%" -c "import PyQt6, fitz, PIL, docx, pdf2docx, odf, pythoncom, win32com.client" >nul 2>nul
if errorlevel 1 goto install_packages

"%VENV_PY%" -m pip check >nul 2>nul
if errorlevel 1 goto install_packages
goto run_program

:install_packages
echo Installing required packages...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto error
"%VENV_PY%" -m pip install -r "requirements.txt"
if errorlevel 1 goto error

:run_program
echo Starting Multifora...
if exist "%VENV_DIR%\Scripts\pythonw.exe" (
    "%VENV_DIR%\Scripts\pythonw.exe" "%~dp0%APP_ENTRY%" %*
) else (
    "%VENV_PY%" "%~dp0%APP_ENTRY%" %*
)
if errorlevel 1 goto error
exit /b 0

:error
echo.
echo ERROR: Multifora could not be started.
echo Review the error message shown above.
echo.
pause
exit /b 1
