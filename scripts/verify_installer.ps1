# Install the generated EXE silently into a temporary per-user directory,
# run the frozen smoke test, then uninstall it.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project

$identity = Get-Content 'app/core/app_identity.py' -Raw
$versionMatch = [regex]::Match($identity, '(?m)^APP_VERSION\s*=\s*["'']([^"'']+)["'']')
if (-not $versionMatch.Success) { throw 'Could not read APP_VERSION' }
$version = $versionMatch.Groups[1].Value
$installer = Join-Path $project "dist/installer/Multifora-Setup-$version.exe"
if (-not (Test-Path $installer)) { throw "Missing installer: $installer" }

$installDir = Join-Path $env:TEMP ([string]::Format('Multifora-InstallTest-{0}', [guid]::NewGuid().ToString('N')))
try {
    $args = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CLOSEAPPLICATIONS', "/DIR=`"$installDir`"")
    $install = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
    if ($install.ExitCode -ne 0) { throw "Installer exit code: $($install.ExitCode)" }

    & python 'scripts/verify_windows_bundle.py' --bundle $installDir
    if ($LASTEXITCODE -ne 0) { throw 'Installed bundle is incomplete' }

    $report = Join-Path $env:TEMP 'multifora-installed-smoke.json'
    $env:MULTIFORA_SMOKE_REPORT = $report
    if (Test-Path $report) { Remove-Item $report -Force }
    $app = Start-Process -FilePath (Join-Path $installDir 'Multifora.exe') -ArgumentList '--build-smoke-test' -Wait -PassThru
    if (Test-Path $report) { Get-Content $report -Raw | Write-Host }
    if ($app.ExitCode -ne 0) { throw "Installed application smoke test failed: $($app.ExitCode)" }
    $result = Get-Content $report -Raw | ConvertFrom-Json
    if ($result.status -ne 'ok' -or -not $result.window_visible) { throw 'Smoke test did not initialize the main window' }
    Write-Host 'Silent installer smoke test passed.'
}
finally {
    $uninstall = Join-Path $installDir 'unins000.exe'
    if (Test-Path $uninstall) {
        $remove = Start-Process -FilePath $uninstall -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru
        if ($remove.ExitCode -ne 0) { Write-Warning "Uninstaller exit code: $($remove.ExitCode)" }
    }
    Remove-Item Env:MULTIFORA_SMOKE_REPORT -ErrorAction SilentlyContinue
}
