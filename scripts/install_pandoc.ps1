[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$version = '3.13'
$expectedSha256 = '23e1f2e978a3df80db8bf65c9c59534f41a23140480cfb4f783a882ab7dc6a4e'
$project = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $project 'bin\pandoc'
$executable = Join-Path $destination 'pandoc.exe'

if (Test-Path -LiteralPath $executable -PathType Leaf) {
    & $executable --version | Select-Object -First 1 | Write-Host
    if ($LASTEXITCODE -ne 0) { throw 'Existing Pandoc executable did not start.' }
    exit 0
}

$temporary = Join-Path ([System.IO.Path]::GetTempPath()) ('multifora-pandoc-' + [guid]::NewGuid())
$archive = Join-Path $temporary 'pandoc.zip'
$expanded = Join-Path $temporary 'expanded'
$url = "https://github.com/jgm/pandoc/releases/download/$version/pandoc-$version-windows-x86_64.zip"

try {
    New-Item -ItemType Directory -Path $temporary, $expanded -Force | Out-Null
    Write-Host "Downloading Pandoc $version..."
    Invoke-WebRequest -Uri $url -OutFile $archive
    $actualSha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $expectedSha256) {
        throw "Pandoc checksum mismatch: expected $expectedSha256, received $actualSha256"
    }

    Expand-Archive -LiteralPath $archive -DestinationPath $expanded
    $source = Join-Path $expanded "pandoc-$version"
    if (-not (Test-Path -LiteralPath (Join-Path $source 'pandoc.exe') -PathType Leaf)) {
        throw 'Downloaded Pandoc archive has an unexpected layout.'
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $source 'pandoc.exe') -Destination $destination -Force
    Copy-Item -LiteralPath (Join-Path $source 'COPYING.rtf') -Destination $destination -Force
    Copy-Item -LiteralPath (Join-Path $source 'COPYRIGHT.txt') -Destination $destination -Force
    & $executable --version | Select-Object -First 1 | Write-Host
    if ($LASTEXITCODE -ne 0) { throw 'Downloaded Pandoc executable did not start.' }
} finally {
    if (Test-Path -LiteralPath $temporary) {
        Remove-Item -LiteralPath $temporary -Recurse -Force
    }
}
