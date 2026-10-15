# Produce a portable ZIP and SHA-256 checksums for all Windows release files.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project

$identity = Get-Content 'app/core/app_identity.py' -Raw
$versionMatch = [regex]::Match($identity, '(?m)^APP_VERSION\s*=\s*["'']([^"'']+)["'']')
if (-not $versionMatch.Success) { throw 'Could not read APP_VERSION' }
$version = $versionMatch.Groups[1].Value

$bundle = Join-Path $project 'dist/Multifora'
$exe = Join-Path $bundle 'Multifora.exe'
if (-not (Test-Path $exe -PathType Leaf)) { throw "Executable missing: $exe" }
$portable = Join-Path $project "dist/Multifora-Portable-$version.zip"
if (Test-Path $portable) { Remove-Item $portable -Force }
Compress-Archive -Path (Join-Path $bundle '*') -DestinationPath $portable -CompressionLevel Optimal

$installer = Join-Path $project "dist/installer/Multifora-Setup-$version.exe"
$artifacts = @($portable)
if (Test-Path $installer -PathType Leaf) { $artifacts += $installer }
$lines = foreach ($artifact in $artifacts) {
    $sha = (Get-FileHash -Path $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
    "$sha  $(Split-Path -Leaf $artifact)"
}
$checksums = Join-Path $project 'dist/SHA256SUMS.txt'
[System.IO.File]::WriteAllLines($checksums, [string[]]$lines, [System.Text.Encoding]::ASCII)
Write-Host "Portable archive: $portable"
if (Test-Path $installer) { Write-Host "Installer: $installer" }
Write-Host "Hashes: $checksums"
