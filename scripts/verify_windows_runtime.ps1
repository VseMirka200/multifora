$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $root 'dist\Multifora'
$executable = Join-Path $bundle 'Multifora.exe'
$pandoc = Join-Path $bundle 'bin\pandoc\pandoc.exe'
$ghostscript = Join-Path $bundle 'bin\gswin64\gswin64c.exe'
$expectedWork = Join-Path ([IO.Path]::GetTempPath()) ('multifora-runtime-' + [guid]::NewGuid().ToString('N'))
$savedProfile = $env:USERPROFILE
$savedPlatform = $env:QT_QPA_PLATFORM

try {
    New-Item -ItemType Directory -Path $expectedWork | Out-Null
    $source = Join-Path $expectedWork 'offline.md'
    $output = Join-Path $expectedWork 'offline.docx'
    Set-Content -LiteralPath $source -Encoding UTF8 -Value '# Offline test'
    & $pandoc --sandbox --from markdown --to docx --output $output -- $source
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $output)) {
        throw 'Pandoc could not convert a document.'
    }
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
    @{ started = $true; observation_ms = $timer.ElapsedMilliseconds; pandoc_offline = $true } |
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
