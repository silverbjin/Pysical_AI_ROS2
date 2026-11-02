# Run only with explicit approval for Windows administrator WslService restart.
# Normal service stop/start only: no process killing, reboot, driver or config edits.
$ErrorActionPreference='Stop'
$record=[ordered]@{
  scope='explicitly_approved_Windows_administrator_WslService_restart_only'
  started=(Get-Date).ToString('o')
  service='WslService'
  source_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
  administrator=$false
  stopped=$false
  started_again=$false
  permanent_settings_changed=$false
  error=$null
}
$code=1
try {
  $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
  $principal=[Security.Principal.WindowsPrincipal]::new($identity)
  $record.administrator=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if(-not $record.administrator){throw 'Windows administrator approval is required; no service action attempted'}
  $service=Get-Service -Name 'WslService'
  $record.initial_status=$service.Status.ToString()
  if($service.Status -ne [ServiceProcess.ServiceControllerStatus]::Stopped){
    $service.Stop()
    $service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Stopped,[TimeSpan]::FromSeconds(20))
  }
  $record.stopped=$true
  $service.Start()
  $service.WaitForStatus([ServiceProcess.ServiceControllerStatus]::Running,[TimeSpan]::FromSeconds(20))
  $record.started_again=$true
  $record.final_status=$service.Status.ToString()
  $code=0
} catch {$record.error=$_.Exception.Message}
finally {
  $record.finished=(Get-Date).ToString('o')
  $record.exit_code=$code
  [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'service-restart-result.json'),($record | ConvertTo-Json -Depth 4),[Text.UTF8Encoding]::new($false))
}
exit $code
