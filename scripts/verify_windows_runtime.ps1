$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $root 'dist\Multifora'
$executable = Join-Path $bundle 'Multifora.exe'
$expectedWork = Join-Path ([IO.Path]::GetTempPath()) ('multifora-runtime-' + [guid]::NewGuid().ToString('N'))
$savedProfile = $env:USERPROFILE
$savedPlatform = $env:QT_QPA_PLATFORM
$savedReport = $env:MULTIFORA_SMOKE_REPORT

try {
    New-Item -ItemType Directory -Path $expectedWork | Out-Null
    $office = Join-Path $bundle 'bin\wordcraft\wordcraft-cli.exe'
    $source = Join-Path $expectedWork 'sample.txt'
    [IO.File]::WriteAllText($source, 'Multifora conversion check', [Text.UTF8Encoding]::new($false))
    & $office convert $source (Join-Path $expectedWork 'sample.pdf')
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $expectedWork 'sample.pdf'))) {
        throw 'Bundled WordCraft conversion failed.'
    }
    $pdfcraft = Join-Path $bundle 'bin\pdfcraft\pdfcraft-cli.exe'
    & $pdfcraft info (Join-Path $expectedWork 'sample.pdf') | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Bundled PDFCraft failed to read a PDF.' }

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
    @{ started = $true; observation_ms = $timer.ElapsedMilliseconds; office_helper = 'WordCraft' } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'dist\runtime-metrics.json') -Encoding UTF8
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
