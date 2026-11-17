$ErrorActionPreference = 'Stop'
$version = '3.14'
$expectedHash = '0144B96E8C7B023FD382EC5EF5BDC475E873F1019D6FA72502492DF2C9A94A3B'
$project = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $project 'bin\pandoc'
$archive = Join-Path ([System.IO.Path]::GetTempPath()) ("multifora-pandoc-{0}-{1}.zip" -f $version, [guid]::NewGuid())
try {
    $url = "https://github.com/jgm/pandoc/releases/download/$version/pandoc-$version-windows-x86_64.zip"
    Invoke-WebRequest -Uri $url -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expectedHash) {
        throw 'Pandoc archive checksum mismatch.'
    }
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($archive)
    try {
        foreach ($name in @('pandoc.exe', 'COPYING.rtf', 'COPYRIGHT.txt')) {
            $entry = $zip.GetEntry("pandoc-$version/$name")
            if ($null -eq $entry) { throw "Missing Pandoc archive entry: $name" }
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, (Join-Path $destination $name), $true)
        }
    } finally {
        $zip.Dispose()
    }
} finally {
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
