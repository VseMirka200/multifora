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
    if ($result.status -ne 'ok' -or -not $result.window_visible -or -not $result.pdf_engine -or -not $result.photo_engine -or -not $result.deck_engine -or -not $result.pdf_roundtrip -or -not $result.pdf_merge -or -not $result.pdf_to_docx -or -not $result.image_roundtrip) {
        throw "Frozen EXE checks failed: $(ConvertTo-Json -InputObject $result -Depth 5)"
    }
    foreach ($engine in @('pdfcraft-cli.exe', 'photocraft-cli.exe', 'deckcraft-cli.exe')) {
        & (Join-Path $bundlePath "bin\native\$engine") --version
        if ($LASTEXITCODE -ne 0) { throw "$engine did not start" }
    }
    $metricsPath = Join-Path (Split-Path $bundlePath -Parent) 'runtime-metrics.json'
    [ordered]@{
        frozen_smoke_seconds = [math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
        window_create_seconds = $result.window_create_seconds
        engines = [ordered]@{
            pdfcraft = $result.pdf_engine
            photocraft = $result.photo_engine
            deckcraft = $result.deck_engine
        }
        checks = [ordered]@{
            pdf_roundtrip = $result.pdf_roundtrip
            pdf_merge = $result.pdf_merge
            pdf_to_docx = $result.pdf_to_docx
            image_roundtrip = $result.image_roundtrip
        }
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $metricsPath -Encoding utf8
    Write-Host 'Frozen EXE and all three ArtCraft native engines verified.'
} finally {
    $env:MULTIFORA_SMOKE_REPORT = $previousReport
    $env:QT_QPA_PLATFORM = $previousPlatform
    if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
}
