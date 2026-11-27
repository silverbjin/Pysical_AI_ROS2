param(
    [string]$Distro = 'Ubuntu-24.04',
    [ValidateRange(1,1200)][int]$Seconds = 620,
    [string]$OutputRoot = (Join-Path $HOME 'ch15-clock-evidence'),
    [string]$NtpServer = '',
    [string]$SourcePin = 'LOCAL_CANDIDATE'
)
$ErrorActionPreference = 'Stop'
$root = Join-Path $OutputRoot ([Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root -Force | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
$status = [ordered]@{ result='COLLECTION_INCOMPLETE'; source_pin=$SourcePin; requested_seconds=$Seconds; phases=@(); acceptance='NOT_EVALUATED' }
function Save-Query([string]$Name,[scriptblock]$Body) {
    try { & $Body 2>&1 | Out-String -Width 240 | Set-Content -Encoding UTF8 (Join-Path $root $Name) }
    catch { "NOT_AVAILABLE: $($_.Exception.Message)" | Set-Content -Encoding UTF8 (Join-Path $root $Name) }
}
function WslPath([string]$Path) {
    $p = (& wsl.exe -d $Distro --exec wslpath -a -u $Path | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $p.StartsWith('/')) { throw 'WSL path conversion failed' }
    return $p
}
function QpcNs {
    return [long]([decimal][Diagnostics.Stopwatch]::GetTimestamp() * 1000000000 / [Diagnostics.Stopwatch]::Frequency)
}
function Write-JsonLine($Writer,$Object) {
    $Writer.WriteLine(($Object | ConvertTo-Json -Depth 8 -Compress))
}
try {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class Ch15PreciseClock {
  [DllImport("kernel32.dll")] public static extern void GetSystemTimePreciseAsFileTime(out long value);
  public static long UtcNs() { long v; GetSystemTimePreciseAsFileTime(out v); return (v-116444736000000000L)*100L; }
}
'@
    Save-Query 'windows-version.txt' { Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber; Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent }
    Save-Query 'wsl-version.txt' { wsl.exe --version; wsl.exe --list --verbose }
    Save-Query 'w32time.txt' { Get-Service W32Time; w32tm.exe /query /source; w32tm.exe /query /status /verbose; w32tm.exe /query /configuration }
    Save-Query 'hyperv-logs.txt' { Get-WinEvent -ListLog '*Hyper-V*' | Select-Object LogName,IsEnabled,RecordCount }
    Save-Query 'time-events-before.txt' { Get-WinEvent -LogName 'Microsoft-Windows-Time-Service/Operational' -MaxEvents 200 | Select-Object TimeCreated,Id,ProviderName,Message | Format-List }
    if ($NtpServer) { Save-Query 'external-before.txt' { w32tm.exe /stripchart /computer:$NtpServer /samples:5 /period:1 } }
    $linuxScript = WslPath (Join-Path $PSScriptRoot 'clock_diag_wsl2.sh')
    $linuxAnalyzer = WslPath (Join-Path (Split-Path $PSScriptRoot -Parent) 'python\clock_cross_layer_analyzer.py')
    function Get-Anchor([string]$Phase) {
        $q0=QpcNs
        $reply=(& wsl.exe -d $Distro --exec bash $linuxScript anchor 2>$null | Out-String).Trim()
        $exit=$LASTEXITCODE
        $q1=QpcNs
        $guest=$null
        if ($exit -eq 0) { try { $guest=$reply | ConvertFrom-Json } catch {} }
        return @{phase=$Phase;qpc_before_ns=$q0;qpc_after_ns=$q1;guest=$guest;exit=$exit}
    }
    foreach ($phase in @('idle','docker')) {
        $dir=Join-Path $root $phase
        New-Item -ItemType Directory -Path $dir | Out-Null
        $linuxOut=WslPath $dir
        $anchorWriter=[IO.StreamWriter]::new((Join-Path $dir 'anchors.jsonl'),$false,$utf8)
        $sampleWriter=[IO.StreamWriter]::new((Join-Path $dir 'windows.jsonl'),$false,$utf8)
        $job=$null
        try {
            1..5 | ForEach-Object { Write-JsonLine $anchorWriter (Get-Anchor 'before') }
            $anchorWriter.Flush()
            $job=Start-Job -ArgumentList $Distro,$linuxScript,$linuxOut,$Seconds,$phase -ScriptBlock {
                param($d,$s,$o,$n,$p)
                & wsl.exe -d $d --exec bash $s $o $n $p
                Write-Output "WSL_EXIT=$LASTEXITCODE"
            }
            $start=QpcNs; $count=0
            while ($job.State -in @('NotStarted','Running')) {
                $a=QpcNs; $v=[Ch15PreciseClock]::UtcNs(); $b=QpcNs
                Write-JsonLine $sampleWriter @{scope='windows';sim_time=$null;monotonic_ns=(QpcNs);reads=@{realtime=@{m0=$a;m1=$b;value_ns=$v}}}
                $count++; if ($count % 20 -eq 0) { $sampleWriter.Flush() }
                if ((QpcNs)-$start -gt ([long]($Seconds*2+300)*1000000000)) { throw 'Windows QPC timeout; inspect owned WSL diagnostic children' }
                Start-Sleep -Milliseconds 50
            }
            $jobResult=Receive-Job $job -ErrorAction Continue | Out-String
            $jobResult | Set-Content -Encoding UTF8 (Join-Path $dir 'wsl-job.txt')
            $sampleWriter.Flush()
            1..5 | ForEach-Object { Write-JsonLine $anchorWriter (Get-Anchor 'after') }
            $anchorWriter.Flush()
            & wsl.exe -d $Distro --exec python3 $linuxAnalyzer $linuxOut | Set-Content -Encoding UTF8 (Join-Path $dir 'cross-analysis.json')
            $analysisExit=$LASTEXITCODE
            $status.phases += @{phase=$phase;windows_samples=$count;wsl_exit0=($jobResult -match 'WSL_EXIT=0');analysis_exit=$analysisExit}
        } finally {
            $sampleWriter.Dispose(); $anchorWriter.Dispose()
            if ($job) { if ($job.State -eq 'Running') { Stop-Job $job }; Remove-Job $job -Force }
        }
    }
    if ($status.phases.Count -eq 2 -and @($status.phases | Where-Object { -not $_.wsl_exit0 -or $_.analysis_exit -ne 0 }).Count -eq 0) { $status.result='COLLECTION_COMPLETE_REVIEW_REQUIRED' }
} catch {
    $status.error=$_.Exception.Message
} finally {
    Save-Query 'hyperv-events.txt' { Get-WinEvent -FilterHashtable @{LogName=@('Microsoft-Windows-Hyper-V-Hypervisor/Operational','Microsoft-Windows-Hyper-V-Worker/Admin','Microsoft-Windows-Hyper-V-VMMS/Admin');StartTime=(Get-Date).AddHours(-2)} -MaxEvents 200 | Select-Object TimeCreated,Id,ProviderName,Message | Format-List }
    Save-Query 'time-events-after.txt' { Get-WinEvent -LogName 'Microsoft-Windows-Time-Service/Operational' -MaxEvents 200 | Select-Object TimeCreated,Id,ProviderName,Message | Format-List }
    Save-Query 'system-events.txt' { Get-WinEvent -FilterHashtable @{LogName='System';ProviderName=@('Microsoft-Windows-Kernel-General','Microsoft-Windows-Kernel-Power','Microsoft-Windows-Power-Troubleshooter','Microsoft-Windows-Time-Service');StartTime=(Get-Date).AddHours(-2)} -MaxEvents 300 | Select-Object TimeCreated,Id,ProviderName,Message | Format-List }
    if ($NtpServer) { Save-Query 'external-after.txt' { w32tm.exe /stripchart /computer:$NtpServer /samples:5 /period:1 } }
    [IO.File]::WriteAllText((Join-Path $root 'status.json'),($status | ConvertTo-Json -Depth 8),$utf8)
    $manifest=@(Get-ChildItem $root -File -Recurse | Sort-Object FullName | ForEach-Object {
        $rel=$_.FullName.Substring($root.Length+1).Replace('\','/')
        ((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()+'  '+$rel)
    })
    [IO.File]::WriteAllLines((Join-Path $root 'manifest.sha256'),[string[]]$manifest,$utf8)
    $zip=$root+'.zip'; Compress-Archive -Path (Join-Path $root '*') -DestinationPath $zip
    $hash=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.File]::WriteAllText(($zip+'.sha256'),($hash+'  '+(Split-Path $zip -Leaf)+"`n"),$utf8)
    Write-Output "$($status.result) — $zip"
    Write-Output 'No clock settings changed. Do not rerun F06/F01. Upload ZIP and SHA256 privately for review.'
}
if ($status.result -ne 'COLLECTION_COMPLETE_REVIEW_REQUIRED') { exit 1 }
