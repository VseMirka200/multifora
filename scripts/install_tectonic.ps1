[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$version = '0.17.0'
$expectedSha256 = 'f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f'
$project = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $project 'bin\tectonic'
$executable = Join-Path $destination 'tectonic.exe'

if (Test-Path -LiteralPath $executable -PathType Leaf) {
    & $executable --version
    if ($LASTEXITCODE -ne 0) { throw 'Existing Tectonic executable did not start.' }
    exit 0
}

$temporary = Join-Path ([System.IO.Path]::GetTempPath()) ('multifora-tectonic-' + [guid]::NewGuid())
$archive = Join-Path $temporary 'tectonic.zip'
$expanded = Join-Path $temporary 'expanded'
$url = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40$version/tectonic-$version-x86_64-pc-windows-msvc.zip"

try {
    New-Item -ItemType Directory -Path $temporary, $expanded -Force | Out-Null
    Write-Host "Downloading Tectonic $version..."
    Invoke-WebRequest -Uri $url -OutFile $archive
    $actualSha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $expectedSha256) {
        throw "Tectonic checksum mismatch: expected $expectedSha256, received $actualSha256"
    }

    Expand-Archive -LiteralPath $archive -DestinationPath $expanded
    $source = Join-Path $expanded 'tectonic.exe'
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw 'Downloaded Tectonic archive has an unexpected layout.'
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
    & $executable --version
    if ($LASTEXITCODE -ne 0) { throw 'Downloaded Tectonic executable did not start.' }
} finally {
    if (Test-Path -LiteralPath $temporary) {
        Remove-Item -LiteralPath $temporary -Recurse -Force
    }
}
