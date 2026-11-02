param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputPath){throw 'Evidence exists; no overwrite'}
$records=[Collections.Generic.List[object]]::new()
$timer=[Diagnostics.Stopwatch]::StartNew()
while($timer.Elapsed.TotalSeconds -lt 90 -and $records.Count -lt 18){
  $before=[DateTimeOffset]::UtcNow
  $q0=[Diagnostics.Stopwatch]::GetTimestamp()
  $cpu=Get-CimInstance -ClassName Win32_PerfFormattedData_Counters_ProcessorInformation -Filter "Name='_Total'" -OperationTimeoutSec 4
  $q1=[Diagnostics.Stopwatch]::GetTimestamp()
  $records.Add([pscustomobject]@{before_utc=$before.ToString('o');after_utc=[DateTimeOffset]::UtcNow.ToString('o');
    qpc_before=$q0;qpc_after=$q1;qpc_frequency=[Diagnostics.Stopwatch]::Frequency;
    elapsed_s=$timer.Elapsed.TotalSeconds;processor_frequency=$cpu.ProcessorFrequency;
    percent_maximum_frequency=$cpu.PercentofMaximumFrequency;percent_processor_performance=$cpu.PercentProcessorPerformance;
    percent_processor_utility=$cpu.PercentProcessorUtility;percent_processor_time=$cpu.PercentProcessorTime})
  Start-Sleep -Seconds 5
}
$data=[pscustomobject]@{scope='read_only_host_aggregate_not_engine_or_thermal_causality';
  method_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLower();
  settings_changed=$false;sampling_target_duration_s=90;query_timeout_s=4;maximum_records=18;records=$records}
$json=$data | ConvertTo-Json -Depth 5
if([Text.Encoding]::UTF8.GetByteCount($json) -gt 65536){throw 'Host telemetry budget exceeded'}
[IO.File]::WriteAllText($OutputPath,$json,[Text.UTF8Encoding]::new($false))
Write-Output "Host CPU evidence closed: $($records.Count) samples"
