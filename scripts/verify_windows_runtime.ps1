param(
    [string]$Bundle = (Join-Path $PSScriptRoot '..\dist\Multifora')
)

$ErrorActionPreference = 'Stop'
$bundlePath = (Resolve-Path -LiteralPath $Bundle).Path
$report = Join-Path ([System.IO.Path]::GetTempPath()) ("multifora-smoke-" + [guid]::NewGuid() + '.json')
$previousReport = $env:MULTIFORA_SMOKE_REPORT
$previousPlatform = $env:QT_QPA_PLATFORM
try {
    $env:MULTIFORA_SMOKE_REPORT = $report
    $env:QT_QPA_PLATFORM = 'offscreen'
    $app = Start-Process -FilePath (Join-Path $bundlePath 'Multifora.exe') -ArgumentList '--build-smoke-test' -WindowStyle Hidden -Wait -PassThru
    if (Test-Path -LiteralPath $report) { Get-Content -LiteralPath $report -Raw | Write-Host }
    if ($app.ExitCode -ne 0) { throw "Frozen EXE failed: $($app.ExitCode)" }
    $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if ($result.status -ne 'ok' -or -not $result.window_visible -or -not $result.pdf_roundtrip -or -not $result.docx_merge) {
        throw "Frozen EXE checks failed: $(ConvertTo-Json -InputObject $result -Depth 5)"
    }
    & (Join-Path $bundlePath 'bin\gswin64\gswin64c.exe') --version
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Ghostscript did not start' }
    & (Join-Path $bundlePath 'bin\pandoc\pandoc.exe') --version
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Pandoc did not start' }
    & (Join-Path $bundlePath 'bin\tectonic\tectonic.exe') --version
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Tectonic did not start' }
    Write-Host 'Frozen EXE, PDF, DOCX merge, Ghostscript, Pandoc and Tectonic verified.'
} finally {
    $env:MULTIFORA_SMOKE_REPORT = $previousReport
    $env:QT_QPA_PLATFORM = $previousPlatform
    if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
}
