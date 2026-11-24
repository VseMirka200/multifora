$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$dist = Join-Path $root 'dist'
$versionLine = Select-String -LiteralPath (Join-Path $root 'app\core\app_identity.py') -Pattern '^APP_VERSION = "([^"]+)"$'
if (-not $versionLine) { throw 'Application version not found.' }
$version = $versionLine.Matches[0].Groups[1].Value
$archive = Join-Path $dist "Multifora-Portable-$version.zip"
Compress-Archive -Path (Join-Path $dist 'Multifora\*') -DestinationPath $archive -Force
$artifacts = @($archive) + @(Get-ChildItem -LiteralPath (Join-Path $dist 'installer') -File | Where-Object { $_.Name -like 'Multifora-Setup-*.exe' -or $_.Name -like 'Multifora-Silent-Install-*.bat' } | ForEach-Object { $_.FullName })
$checksums = foreach ($artifact in $artifacts) {
    $hash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
    $relative = [IO.Path]::GetRelativePath($dist, $artifact).Replace('\', '/')
    "$hash  $relative"
}
$checksums | Set-Content -LiteralPath (Join-Path $dist 'SHA256SUMS.txt') -Encoding ascii
