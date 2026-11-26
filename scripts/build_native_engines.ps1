[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$NativeDir = Join-Path $ProjectRoot 'bin\native'
$SourceRoot = Join-Path $env:TEMP 'multifora-artcraft-engines'
$TargetRoot = Join-Path $ProjectRoot '.cargo-native-target'

$Engines = @(
    @{ Name = 'pdfcraft'; Repository = 'https://github.com/storytold/pdfcraft.git'; Tag = 'v0.22.0'; Package = 'pdfcraft-cli'; Binary = 'pdfcraft-cli.exe'; Arguments = @('--no-default-features') },
    @{ Name = 'photocraft'; Repository = 'https://github.com/storytold/photocraft.git'; Tag = 'v0.23.1'; Package = 'photocraft-cli'; Binary = 'photocraft-cli.exe'; Arguments = @('--no-default-features', '--features', 'heif') },
    @{ Name = 'deckcraft'; Repository = 'https://github.com/storytold/deckcraft.git'; Tag = 'v0.19.1'; Package = 'deckcraft-cli'; Binary = 'deckcraft-cli.exe'; Arguments = @() }
)

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is required to fetch the pinned ArtCraft engine sources.'
}
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    throw 'Rust/Cargo 1.95.0 is required. Install it with rustup before building native engines.'
}
$rustVersion = (& rustc --version)
if ($LASTEXITCODE -ne 0 -or $rustVersion -notmatch '1\.95\.') {
    throw "Rust 1.95.x is required; found: $rustVersion"
}

New-Item -ItemType Directory -Force -Path $NativeDir, $SourceRoot, $TargetRoot | Out-Null
# Purge legacy conversion runtimes from developer builds and release staging.
foreach ($legacyDirectory in @('pandoc', 'tectonic', 'gswin64')) {
    $legacyPath = Join-Path (Join-Path $ProjectRoot 'bin') $legacyDirectory
    if (Test-Path -LiteralPath $legacyPath) {
        Remove-Item -LiteralPath $legacyPath -Recurse -Force
    }
}
$env:CARGO_TARGET_DIR = $TargetRoot
$env:CARGO_INCREMENTAL = '0'

foreach ($engine in $Engines) {
    $binaryPath = Join-Path $NativeDir $engine.Binary
    $licenseDir = Join-Path $NativeDir 'licenses' $engine.Name
    $licenseComplete = (Test-Path -LiteralPath (Join-Path $licenseDir 'LICENSE-MIT')) -and (Test-Path -LiteralPath (Join-Path $licenseDir 'LICENSE-APACHE'))
    if ((Test-Path -LiteralPath $binaryPath) -and $licenseComplete -and -not $Force) {
        & $binaryPath --version *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "$($engine.Name): executable and license bundle already verified."
            continue
        }
    }

    $sourcePath = Join-Path $SourceRoot $engine.Name
    if (Test-Path -LiteralPath $sourcePath) {
        Remove-Item -LiteralPath $sourcePath -Recurse -Force
    }
    Write-Host "Fetching $($engine.Name) $($engine.Tag)..."
    & git clone --depth 1 --branch $engine.Tag $engine.Repository $sourcePath
    if ($LASTEXITCODE -ne 0) { throw "Git clone failed for $($engine.Name)." }

    Push-Location $sourcePath
    try {
        Write-Host "Building $($engine.Name) CLI (Windows x64, release)..."
        $cargoArgs = @('build', '--locked', '--release', '--package', $engine.Package, '--bin', $engine.Binary.Replace('.exe', '')) + $engine.Arguments
        & cargo @cargoArgs
        if ($LASTEXITCODE -ne 0) { throw "Cargo build failed for $($engine.Name)." }

        $builtBinary = Join-Path (Join-Path $TargetRoot 'release') $engine.Binary
        if (-not (Test-Path -LiteralPath $builtBinary)) {
            throw "Cargo did not produce $($engine.Binary)."
        }
        Copy-Item -LiteralPath $builtBinary -Destination $binaryPath -Force

        if (Test-Path -LiteralPath $licenseDir) {
            Remove-Item -LiteralPath $licenseDir -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path $licenseDir | Out-Null
        foreach ($licenseFile in @('LICENSE-MIT', 'LICENSE-APACHE', 'LICENSES.toml', 'NOTICE')) {
            $candidate = Join-Path $sourcePath $licenseFile
            if (Test-Path -LiteralPath $candidate) {
                Copy-Item -LiteralPath $candidate -Destination $licenseDir -Force
            }
        }
        # Preserve every upstream copyright, license, attribution and notice file
        # at its original relative path (including bundled font/codec notices).
        Get-ChildItem -LiteralPath $sourcePath -Recurse -File |
            Where-Object { $_.Name -match '^(LICENSE|NOTICE|ATTRIBUTION|COPYING|OFL)' } |
            ForEach-Object {
                $relative = $_.FullName.Substring($sourcePath.Length).TrimStart([char[]]@(92, 47))
                $destination = Join-Path $licenseDir $relative
                $destinationFolder = Split-Path -Parent $destination
                New-Item -ItemType Directory -Force -Path $destinationFolder | Out-Null
                Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
            }
        $upstreamLicenses = Join-Path $sourcePath 'licenses'
        if (Test-Path -LiteralPath $upstreamLicenses) {
            Copy-Item -LiteralPath $upstreamLicenses -Destination $licenseDir -Recurse -Force
        }
        $readme = Join-Path $licenseDir 'UPSTREAM.txt'
        @(
            "$($engine.Name) $($engine.Tag)",
            $engine.Repository.Replace('.git', ''),
            'Built from the unmodified upstream source at the pinned release tag.',
            'The upstream project declares MIT OR Apache-2.0; see the included license and attribution files.'
        ) | Set-Content -LiteralPath $readme -Encoding utf8
    }
    finally {
        Pop-Location
    }

    & $binaryPath --version
    if ($LASTEXITCODE -ne 0) { throw "$($engine.Binary) failed its version smoke test." }
}

$manifest = @'
ArtCraft native engines bundled with Multifora:
- PdfCraft CLI 0.22.0 — https://github.com/storytold/pdfcraft — MIT OR Apache-2.0
- PhotoCraft CLI 0.23.1 — https://github.com/storytold/photocraft — MIT OR Apache-2.0
- DeckCraft CLI 0.19.1 — https://github.com/storytold/deckcraft — MIT OR Apache-2.0

The executables are built from the unmodified tagged upstream sources. Each engine's
LICENSE-MIT, LICENSE-APACHE, LICENSES.toml, NOTICE (when present), and upstream
licenses/ directory are copied beside the binaries under bin/native/licenses/.
The Rust crate dependency notices and bundled font/codec notices are retained there.
The names ArtCraft, PdfCraft, PhotoCraft and DeckCraft identify their respective
upstream projects; Multifora is an independent integration and is not their publisher.
'@
$manifest | Set-Content -LiteralPath (Join-Path $NativeDir 'THIRD_PARTY_NOTICES.txt') -Encoding utf8
Write-Host 'All pinned ArtCraft native engines are ready in bin/native.'
