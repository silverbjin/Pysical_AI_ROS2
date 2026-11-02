# DO NOT EXECUTE without separate explicit approval for ONE forced WslService exit.
# Pin the already-observed StopPending service PID. Never kill another process,
# change configuration, restart another service, or reboot Windows.
$ErrorActionPreference='Stop'
$record=[ordered]@{
  scope='requires_separate_approval_one_pinned_WslService_force_exit_then_start'
  started=(Get-Date).ToString('o')
  service='WslService'
  expected_pid=10312
  source_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
  administrator=$false
  force_exit_attempted=$false
  force_exit_confirmed=$false
  running_restored=$false
  permanent_settings_changed=$false
  error=$null
}
$code=1
try {
  $principal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
  $record.administrator=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if(-not $record.administrator){throw 'Administrator approval required; no action attempted'}
  $state=Get-CimInstance -ClassName Win32_Service -Filter "Name='WslService'"
  $record.initial_status=$state.State
  $record.observed_pid=$state.ProcessId
  if($state.State -ne 'Stop Pending' -or $state.ProcessId -ne 10312){throw 'Reviewed service/PID/state changed; force exit aborted'}
  $process=Get-Process -Id 10312
  if($process.ProcessName -ne 'wslservice'){throw 'Pinned PID is not WslService; force exit aborted'}
  $record.force_exit_attempted=$true
  Stop-Process -Id 10312 -Force
  if(-not $process.WaitForExit(10000)){throw 'Pinned service process exit unconfirmed'}
  $record.force_exit_confirmed=$true
  $until=[DateTime]::UtcNow.AddSeconds(20)
  do {
    $service=Get-Service -Name 'WslService'
    if($service.Status -eq [ServiceProcess.ServiceControllerStatus]::Running){break}
    if($service.Status -eq [ServiceProcess.ServiceControllerStatus]::Stopped){
      $service.Start()
      $service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Running,[TimeSpan]::FromSeconds(20))
      break
    }
    Start-Sleep -Milliseconds 200
  } while([DateTime]::UtcNow -lt $until)
  $service.Refresh()
  $record.final_status=$service.Status.ToString()
  if($service.Status -ne [ServiceProcess.ServiceControllerStatus]::Running){throw 'WSL service running state unconfirmed; no further action'}
  $record.running_restored=$true
  $code=0
} catch {$record.error=$_.Exception.Message}
finally {
  $record.finished=(Get-Date).ToString('o')
  $record.exit_code=$code
  [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'pinned-service-recovery-result.json'),($record | ConvertTo-Json -Depth 4),[Text.UTF8Encoding]::new($false))
}
exit $code
