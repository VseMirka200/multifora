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
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $app = Start-Process -FilePath (Join-Path $bundlePath 'Multifora.exe') -ArgumentList '--build-smoke-test' -WindowStyle Hidden -Wait -PassThru
    $stopwatch.Stop()
    if (Test-Path -LiteralPath $report) { Get-Content -LiteralPath $report -Raw | Write-Host }
    if ($app.ExitCode -ne 0) { throw "Frozen EXE failed: $($app.ExitCode)" }
    $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if ($result.status -ne 'ok' -or -not $result.window_visible -or -not $result.lazy_backends -or -not $result.image_roundtrip -or -not $result.odf_roundtrip -or -not $result.pdf_roundtrip -or -not $result.pdf_to_docx -or -not $result.docx_merge) {
        throw "Frozen EXE checks failed: $(ConvertTo-Json -InputObject $result -Depth 5)"
    }
    & (Join-Path $bundlePath 'bin\gswin64\gswin64c.exe') --version
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Ghostscript did not start' }
    & (Join-Path $bundlePath 'bin\pandoc\pandoc.exe') --version
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Pandoc did not start' }
    & (Join-Path $bundlePath 'bin\tectonic\tectonic.exe') --version
    if ($LASTEXITCODE -ne 0) { throw 'Bundled Tectonic did not start' }
    $metricsPath = Join-Path (Split-Path $bundlePath -Parent) 'runtime-metrics.json'
    [ordered]@{
        frozen_smoke_seconds = [math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
        window_create_seconds = $result.window_create_seconds
        checks = [ordered]@{
            lazy_backends = $result.lazy_backends
            image_roundtrip = $result.image_roundtrip
            odf_roundtrip = $result.odf_roundtrip
            pdf_roundtrip = $result.pdf_roundtrip
            pdf_to_docx = $result.pdf_to_docx
            docx_merge = $result.docx_merge
        }
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $metricsPath -Encoding utf8
    Write-Host 'Frozen EXE, PDF, DOCX merge, Ghostscript, Pandoc and Tectonic verified.'
} finally {
    $env:MULTIFORA_SMOKE_REPORT = $previousReport
    $env:QT_QPA_PLATFORM = $previousPlatform
    if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
}
