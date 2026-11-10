@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Multifora

set "APP_ENTRY=multifora_start.py"
set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "PYTHON_EXE="

if not exist "%APP_ENTRY%" (
    echo.
    echo ERROR: %APP_ENTRY% was not found.
    echo Keep start_multifora.bat in the project root directory.
    goto error
)

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys" >nul 2>nul
    if not errorlevel 1 goto venv_ready
    echo ERROR: The existing virtual environment cannot be started.
    echo Repair or remove "%VENV_DIR%" and run this file again.
    goto error
)

where py.exe >nul 2>nul
if not errorlevel 1 (
    py.exe -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=py.exe"
        goto python_found
    )
)

where python.exe >nul 2>nul
if not errorlevel 1 (
    python.exe -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=python.exe"
        goto python_found
    )
)

for /d %%D in ("%LocalAppData%\Python\pythoncore-*" "%LocalAppData%\Programs\Python\Python*") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_EXE=%%~D\python.exe"
            goto python_found
        )
    )
)

echo.
echo ERROR: Python was not found or could not be started.
echo Install Python from: https://www.python.org/downloads/windows/
echo Then run start_multifora.bat again.
goto error

:python_found
echo Creating virtual environment...
"%PYTHON_EXE%" -m venv "%VENV_DIR%"
if errorlevel 1 goto error
if not exist "%VENV_PY%" (
    echo ERROR: The virtual environment was not created.
    goto error
)

:venv_ready
set "PYTHONNOUSERSITE=1"

echo Checking required packages...
"%VENV_PY%" -c "import PySide6, pymupdf, PIL, docx, pdf2docx, odf" >nul 2>nul
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
    start "" /b "%VENV_DIR%\Scripts\pythonw.exe" "%~dp0%APP_ENTRY%" %*
    exit /b 0
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
