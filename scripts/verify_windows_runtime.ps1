$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $root 'dist\Multifora'
$executable = Join-Path $bundle 'Multifora.exe'
$tectonic = Join-Path $bundle 'bin\tectonic\tectonic.exe'
$ghostscript = Join-Path $bundle 'bin\gswin64\gswin64c.exe'
$seed = Join-Path $bundle 'bin\tectonic\cache'
$expectedWork = Join-Path ([IO.Path]::GetTempPath()) ('multifora-runtime-' + [guid]::NewGuid().ToString('N'))
$savedCache = $env:TECTONIC_CACHE_DIR
$savedProfile = $env:USERPROFILE
$savedPlatform = $env:QT_QPA_PLATFORM

try {
    New-Item -ItemType Directory -Path $expectedWork | Out-Null
    Copy-Item -LiteralPath $seed -Destination (Join-Path $expectedWork 'cache') -Recurse
    $env:TECTONIC_CACHE_DIR = Join-Path $expectedWork 'cache'
    $tex = Join-Path $expectedWork 'offline.tex'
    Set-Content -LiteralPath $tex -Encoding ascii -Value '\documentclass{article}\begin{document}Offline test\end{document}'
    & $tectonic --untrusted --only-cached --outdir $expectedWork $tex
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $expectedWork 'offline.pdf'))) {
        throw 'Tectonic could not create a PDF using the bundled offline resources.'
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
    @{ started = $true; observation_ms = $timer.ElapsedMilliseconds; tectonic_offline = $true } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'dist\runtime-metrics.json') -Encoding UTF8
} finally {
    $env:TECTONIC_CACHE_DIR = $savedCache
    $env:USERPROFILE = $savedProfile
    $env:QT_QPA_PLATFORM = $savedPlatform
    if (Test-Path -LiteralPath $expectedWork) {
        $resolved = (Resolve-Path -LiteralPath $expectedWork).Path
        if ($resolved -ne $expectedWork) { throw "Unexpected temporary directory: $resolved" }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
