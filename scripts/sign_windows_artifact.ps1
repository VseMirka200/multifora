# Sign a release binary with a certificate supplied as GitHub Actions secrets.
# The private key is imported into the ephemeral runner's user certificate store;
# its password is never put on the signtool command line.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9A-Fa-f]{64}$')]
    [string]$ExpectedCertificateSha256
)

$ErrorActionPreference = 'Stop'
$pfxBase64 = $env:MULTIFORA_CODESIGN_PFX_BASE64
$pfxPassword = $env:MULTIFORA_CODESIGN_PFX_PASSWORD
if ([string]::IsNullOrWhiteSpace($pfxBase64) -or [string]::IsNullOrWhiteSpace($pfxPassword)) {
    throw 'Code-signing PFX and password secrets must both be configured.'
}

$resolvedFile = (Resolve-Path -LiteralPath $FilePath -ErrorAction Stop).Path
$signtoolCommand = Get-Command signtool.exe -ErrorAction SilentlyContinue |
    Select-Object -First 1
$signTool = if ($signtoolCommand) { $signtoolCommand.Source } else { $null }
if (-not $signTool) {
    $sdk = Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Windows Kits\10\bin'
    if (Test-Path -LiteralPath $sdk) {
        $signTool = Get-ChildItem -Path (Join-Path $sdk '*\x64\signtool.exe') -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1 -ExpandProperty FullName
    }
}
if (-not $signTool) {
    throw 'Windows SDK signtool.exe is not installed.'
}

try {
    $pfxBytes = [Convert]::FromBase64String($pfxBase64)
} catch [FormatException] {
    throw 'The code-signing PFX secret is not valid Base64.'
}

$temporaryDir = Join-Path ([System.IO.Path]::GetTempPath()) ("multifora-sign-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporaryDir -ErrorAction Stop | Out-Null
$pfxPath = Join-Path $temporaryDir 'release-signing.pfx'
$importedCertificates = @()
try {
    [System.IO.File]::WriteAllBytes($pfxPath, $pfxBytes)
    $securePassword = ConvertTo-SecureString $pfxPassword -AsPlainText -Force
    $importedCertificates = @(
        Import-PfxCertificate -FilePath $pfxPath -CertStoreLocation 'Cert:\CurrentUser\My' -Password $securePassword -ErrorAction Stop
    )
    $signerCertificate = $null
    foreach ($certificate in $importedCertificates) {
        if (-not $certificate.HasPrivateKey) { continue }
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        try {
            $fingerprint = [BitConverter]::ToString(
                $sha256.ComputeHash($certificate.RawData)
            ).Replace('-', '')
        } finally {
            $sha256.Dispose()
        }
        if ($fingerprint -ceq $ExpectedCertificateSha256.ToUpperInvariant()) {
            $signerCertificate = $certificate
            break
        }
    }
    if ($null -eq $signerCertificate) {
        throw 'No signing key in the PFX matches the pinned DER certificate SHA-256.'
    }
    if ($signerCertificate.NotBefore -gt (Get-Date) -or $signerCertificate.NotAfter -lt (Get-Date)) {
        throw 'The code-signing certificate is not within its validity period.'
    }

    & $signTool sign /s My /sha1 $signerCertificate.Thumbprint /fd SHA256 /tr 'http://timestamp.digicert.com' /td SHA256 $resolvedFile
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed to sign $resolvedFile (exit code: $LASTEXITCODE)."
    }
    & (Join-Path $PSScriptRoot 'verify_authenticode.ps1') -FilePath $resolvedFile -ExpectedCertificateSha256 $ExpectedCertificateSha256
} finally {
    foreach ($certificate in $importedCertificates) {
        $storePath = "Cert:\CurrentUser\My\$($certificate.Thumbprint)"
        if (Test-Path -LiteralPath $storePath) {
            Remove-Item -LiteralPath $storePath -Force -ErrorAction Stop
        }
    }
    if (Test-Path -LiteralPath $temporaryDir) {
        Remove-Item -LiteralPath $temporaryDir -Recurse -Force
    }
}
