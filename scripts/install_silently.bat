@echo off
setlocal EnableExtensions

rem Keep this file next to exactly one Multifora-Setup-*.exe installer.
set "installer="
set /a installer_count=0
for %%I in ("%~dp0Multifora-Setup-*.exe") do (
    if exist "%%~fI" (
        set /a installer_count+=1
        set "installer=%%~fI"
    )
)

if not "%installer_count%"=="1" (
    echo ERROR: Put this file next to exactly one Multifora-Setup-*.exe file.
    exit /b 1
)

echo Installing Multifora silently...
start "" /wait "%installer%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /CLOSEAPPLICATIONS
set "exit_code=%errorlevel%"
if not "%exit_code%"=="0" echo ERROR: Installer exited with code %exit_code%.
exit /b %exit_code%
