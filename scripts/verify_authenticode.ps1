# Verify the Windows trust status and the exact signer certificate (DER SHA-256).
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9A-Fa-f]{64}$')]
    [string]$ExpectedCertificateSha256
)

$ErrorActionPreference = 'Stop'
$resolvedFile = (Resolve-Path -LiteralPath $FilePath -ErrorAction Stop).Path
$signature = Get-AuthenticodeSignature -LiteralPath $resolvedFile

if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
    throw "Authenticode verification failed for $resolvedFile (status: $($signature.Status))."
}
if ($null -eq $signature.SignerCertificate) {
    throw 'An Authenticode signer certificate is missing.'
}

$hasher = [System.Security.Cryptography.SHA256]::Create()
try {
    $actualSha256 = [BitConverter]::ToString(
        $hasher.ComputeHash($signature.SignerCertificate.RawData)
    ).Replace('-', '')
} finally {
    $hasher.Dispose()
}

if ($actualSha256 -cne $ExpectedCertificateSha256.ToUpperInvariant()) {
    throw "Signer certificate SHA-256 does not match the trusted release identity."
}
Write-Host "Authenticode OK; trusted signer certificate SHA-256: $actualSha256"
