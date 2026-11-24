param(
    [string]$BundleDirectory,
    [string]$MetricsPath
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $BundleDirectory) { $BundleDirectory = Join-Path $root 'dist\Multifora' }
if (-not $MetricsPath) { $MetricsPath = Join-Path $root 'dist\runtime-metrics.json' }
$executable = Join-Path $BundleDirectory 'Multifora.exe'
$expectedWork = Join-Path ([IO.Path]::GetTempPath()) ('multifora-runtime-' + [guid]::NewGuid().ToString('N'))
$savedProfile = $env:USERPROFILE
$savedPlatform = $env:QT_QPA_PLATFORM
$savedReport = $env:MULTIFORA_SMOKE_REPORT

try {
    New-Item -ItemType Directory -Path $expectedWork | Out-Null
    $env:USERPROFILE = $expectedWork
    $env:QT_QPA_PLATFORM = 'offscreen'
    $env:MULTIFORA_SMOKE_REPORT = Join-Path $expectedWork 'smoke-report.json'
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $process = Start-Process -FilePath $executable -ArgumentList '--build-smoke-test' -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(60000)) {
        $process.Kill()
        $process.WaitForExit()
        throw 'Application smoke test timed out.'
    }
    $timer.Stop()
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $env:MULTIFORA_SMOKE_REPORT)) {
        throw "Application smoke test failed: $($process.ExitCode)"
    }
    $report = Get-Content -LiteralPath $env:MULTIFORA_SMOKE_REPORT -Raw | ConvertFrom-Json
    if ($report.status -ne 'ok') { throw "Application smoke test failed: $($report | ConvertTo-Json -Compress -Depth 10)" }
    @{ started = $true; observation_ms = $timer.ElapsedMilliseconds; office_backend = 'Python' } |
        ConvertTo-Json | Set-Content -LiteralPath $MetricsPath -Encoding UTF8
} finally {
    $env:USERPROFILE = $savedProfile
    $env:QT_QPA_PLATFORM = $savedPlatform
    $env:MULTIFORA_SMOKE_REPORT = $savedReport
    if (Test-Path -LiteralPath $expectedWork) {
        $resolved = (Resolve-Path -LiteralPath $expectedWork).Path
        if ($resolved -ne $expectedWork) { throw "Unexpected temporary directory: $resolved" }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
