$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $root 'dist\Multifora'
$executable = Join-Path $bundle 'Multifora.exe'
$ghostscript = Join-Path $bundle 'bin\gswin64\gswin64c.exe'
$expectedWork = Join-Path ([IO.Path]::GetTempPath()) ('multifora-runtime-' + [guid]::NewGuid().ToString('N'))
$savedProfile = $env:USERPROFILE
$savedPlatform = $env:QT_QPA_PLATFORM

try {
    New-Item -ItemType Directory -Path $expectedWork | Out-Null
    $wordScript = Join-Path $bundle '_internal\core\workers\office_word.ps1'
    if (-not (Test-Path -LiteralPath $wordScript)) { throw 'Word automation helper is missing.' }
    & $ghostscript --version
    if ($LASTEXITCODE -ne 0) { throw 'Ghostscript failed to start.' }

    $env:USERPROFILE = $expectedWork
    $env:QT_QPA_PLATFORM = 'offscreen'
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $process = Start-Process -FilePath $executable -WindowStyle Hidden -PassThru
    if ($process.WaitForExit(5000)) { throw "Application exited during startup: $($process.ExitCode)" }
    $timer.Stop()
    $process.Kill()
    $process.WaitForExit()
    @{ started = $true; observation_ms = $timer.ElapsedMilliseconds; office_helper = $true } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'dist\runtime-metrics.json') -Encoding UTF8
} finally {
    $env:USERPROFILE = $savedProfile
    $env:QT_QPA_PLATFORM = $savedPlatform
    if (Test-Path -LiteralPath $expectedWork) {
        $resolved = (Resolve-Path -LiteralPath $expectedWork).Path
        if ($resolved -ne $expectedWork) { throw "Unexpected temporary directory: $resolved" }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
