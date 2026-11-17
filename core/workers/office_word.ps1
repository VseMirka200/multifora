param(
    [string]$Source,
    [string]$Output,
    [ValidateSet('PDF', 'DOCX', 'ODT', 'RTF', 'TXT', 'HTML')][string]$Target = 'PDF',
    [Parameter(Mandatory=$true)][string]$PidFile,
    [switch]$Cleanup
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
if ($Cleanup) {
    if (Test-Path -LiteralPath $PidFile) {
        $owner = Get-Content -LiteralPath $PidFile -Raw | ConvertFrom-Json
        $process = Get-Process -Id $owner.process_id -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -eq 'WINWORD' -and
            $process.StartTime.ToUniversalTime().Ticks.ToString() -eq $owner.start_ticks) {
            Stop-Process -Id $process.Id -Force
        }
    }
    exit 0
}
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class MultiforaWordProcess {
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint processId);
}
'@
$word = $null
$document = $null
$probe = $null
$ownsWord = $false
$existingWordProcesses = @(Get-Process -Name WINWORD -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $probe = $word.Documents.Add()
    [uint32]$wordProcessId = 0
    [MultiforaWordProcess]::GetWindowThreadProcessId([IntPtr]$word.ActiveWindow.Hwnd, [ref]$wordProcessId) | Out-Null
    if ($wordProcessId -eq 0 -or $existingWordProcesses -contains $wordProcessId) {
        throw 'Word did not create a separate automation process.'
    }
    $ownsWord = $true
    $process = Get-Process -Id $wordProcessId
    @{ process_id = $wordProcessId; start_ticks = $process.StartTime.ToUniversalTime().Ticks.ToString() } |
        ConvertTo-Json | Set-Content -LiteralPath $PidFile -Encoding UTF8
    $probe.Close(0)
    [Runtime.InteropServices.Marshal]::FinalReleaseComObject($probe) | Out-Null
    $probe = $null
    $document = $word.Documents.Open($Source, $false, $true, $false)
    if ($Target -eq 'PDF') {
        $document.ExportAsFixedFormat($Output, 17)
    } else {
        $format = @{ DOCX = 16; ODT = 23; RTF = 6; TXT = 7; HTML = 10 }[$Target]
        if ($Target -in @('TXT', 'HTML')) {
            $missing = [Type]::Missing
            $encoding = 65001
            $recent = $false
            $document.SaveAs2(
                [ref]$Output, [ref]$format, [ref]$missing, [ref]$missing,
                [ref]$recent, [ref]$missing, [ref]$missing, [ref]$missing,
                [ref]$missing, [ref]$missing, [ref]$missing, [ref]$encoding
            )
        } else {
            $document.SaveAs2([ref]$Output, [ref]$format)
        }
    }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
} finally {
    if ($null -ne $probe) {
        try { $probe.Close(0) } catch { }
        [Runtime.InteropServices.Marshal]::FinalReleaseComObject($probe) | Out-Null
    }
    if ($null -ne $document) {
        try { $document.Close(0) } catch { }
        [Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) | Out-Null
    }
    if ($null -ne $word) {
        if ($ownsWord) { try { $word.Quit(0) } catch { } }
        [Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
    }
}
