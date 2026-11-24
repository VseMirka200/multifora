param([string]$SetupDirectory)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $SetupDirectory) { $SetupDirectory = Join-Path $root 'dist\installer' }
$installers = @(Get-ChildItem -LiteralPath $setupDirectory -Filter 'Multifora-Setup-*.exe')
if ($installers.Count -ne 1) { throw 'Expected exactly one installer.' }

$uninstallKey = '{52A0322B-B489-42FC-A4E9-25B69CE180EC}_is1'
$registryRoots = @(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
)
foreach ($registryRoot in $registryRoots) {
    if (Test-Path -LiteralPath (Join-Path $registryRoot $uninstallKey)) {
        throw 'An existing Multifora installation was found; refusing to modify it during the installer test.'
    }
}

$expectedWork = Join-Path ([IO.Path]::GetTempPath()) ('multifora-installer-' + [guid]::NewGuid().ToString('N'))
$installDirectory = Join-Path $expectedWork 'app'
$uninstaller = Join-Path $installDirectory 'unins000.exe'
$shortcutPath = Join-Path ([Environment]::GetFolderPath('CommonPrograms')) 'Multifora.lnk'
if (Test-Path -LiteralPath $shortcutPath) { throw 'An existing Multifora Start menu shortcut was found.' }
try {
    New-Item -ItemType Directory -Path $expectedWork | Out-Null
    $log = Join-Path $expectedWork 'setup.log'
    $arguments = @(
        '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
        "/DIR=`"$installDirectory`"", "/LOG=`"$log`""
    )
    $setup = Start-Process -FilePath $installers[0].FullName -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
    if ($setup.ExitCode -ne 0) {
        if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Tail 25 }
        throw "Installer failed: $($setup.ExitCode)"
    }
    foreach ($relative in @('Multifora.exe', '_internal\pypdfium2_raw\pdfium.dll')) {
        if (-not (Test-Path -LiteralPath (Join-Path $installDirectory $relative))) {
            throw "Installer did not copy $relative"
        }
    }
    foreach ($relative in @('bin\wordcraft\wordcraft-cli.exe', 'bin\pdfcraft\pdfcraft-cli.exe')) {
        if (Test-Path -LiteralPath (Join-Path $installDirectory $relative)) {
            throw "Installer included legacy engine: $relative"
        }
    }
    if (-not (Test-Path -LiteralPath $shortcutPath -PathType Leaf)) { throw 'Installer did not create the Start menu shortcut.' }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    if ($shortcut.TargetPath -ne (Join-Path $installDirectory 'Multifora.exe')) {
        throw "Unexpected Start menu shortcut target: $($shortcut.TargetPath)"
    }
    & (Join-Path $PSScriptRoot 'verify_windows_runtime.ps1') `
        -BundleDirectory $installDirectory -MetricsPath (Join-Path $expectedWork 'runtime-metrics.json')
} finally {
    try {
        if (Test-Path -LiteralPath $uninstaller) {
            $remove = Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -WindowStyle Hidden -Wait -PassThru
            if ($remove.ExitCode -ne 0) { throw "Test uninstall failed: $($remove.ExitCode)" }
            if ((Test-Path -LiteralPath (Join-Path $installDirectory 'Multifora.exe')) -or
                (Test-Path -LiteralPath $shortcutPath)) { throw 'Uninstaller left application files or its Start menu shortcut.' }
            foreach ($registryRoot in $registryRoots) {
                if (Test-Path -LiteralPath (Join-Path $registryRoot $uninstallKey)) {
                    throw 'Uninstaller left the registration in Windows.'
                }
            }
        }
    } finally {
        if (Test-Path -LiteralPath $expectedWork) {
            $resolved = (Resolve-Path -LiteralPath $expectedWork).Path
            if ($resolved -ne $expectedWork) { throw "Unexpected temporary directory: $resolved" }
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
}
