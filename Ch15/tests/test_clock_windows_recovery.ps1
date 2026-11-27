$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../scripts/clock_diag_windows_recovery.ps1') -LibraryOnly
function Assert($C,[string]$Label){if(-not $C){throw "ASSERT $Label"};Write-Host "PASS $Label"}
function Reject([scriptblock]$Body,[string]$Pattern){
    $caught=$false;try{& $Body}catch{if($_.Exception.Message -match $Pattern){$caught=$true}else{throw}}
    Assert $caught $Pattern
}
$s=@{state='Stopped';start=3;delayed=$null;type='NTP';peers='time.windows.com,0x9';ntp_enabled=1}
$m=@{domain=$false;policy=$false;mdm_policy=$false;mdm_url=$false;enrollment=$false;identity=@{AzureAdJoined='NO';EnterpriseJoined='NO';DomainJoined='NO';WorkplaceJoined='NO'}}
Check-Preflight $s $m;Assert $true 'standalone allowed'
$m.domain=$true;Reject {Check-Preflight $s $m} 'MANAGED_OR_UNKNOWN';$m.domain=$false
$m.identity.WorkplaceJoined='UNKNOWN';Reject {Check-Preflight $s $m} 'MANAGED_OR_UNKNOWN';$m.identity.WorkplaceJoined='NO'
$m.policy=$true;Reject {Check-Preflight $s $m} 'MANAGED_OR_UNKNOWN';$m.policy=$false
$s.start=4;Reject {Check-Preflight $s $m} 'UNSUPPORTED_CONFIG';$s.start=3
$s.type='NT5DS';Reject {Check-Preflight $s $m} 'UNSUPPORTED_CONFIG';$s.type='NTP'
$v=@(Parse-Offsets (@('12:00:00, +0.045s','12:00:01, -0,030s','12:00:02, error: 0x800705B4') -join [Environment]::NewLine))
Assert ($v.Count -eq 2 -and $v[0] -eq .045 -and $v[1] -eq -.03) 'offset parsing'
$good=@(@{reachable=$true;count=4;median_s=.03;max_abs_s=.05},@{reachable=$true;count=5;median_s=-.02;max_abs_s=.04})
Assert (Check-Offsets $good) 'two references'
$good[1].max_abs_s=.3;Assert (-not (Check-Offsets $good)) 'reject outlier';Assert (Check-Offsets $good -ReachableOnly) 'baseline reachability'
$good[1].max_abs_s=.04;$good[1].count=3;Assert (-not (Check-Offsets $good)) 'reject missing samples';$good[1].count=5
Assert (Check-Source @{source='time.windows.com,0x9';source_exit=0;status_exit=0} $s) 'configured source'
Assert (-not (Check-Source @{source='Local CMOS Clock';source_exit=0;status_exit=0} $s)) 'reject local clock'
$script:fake=$s.Clone();$script:calls=New-Object 'System.Collections.Generic.List[string]';$script:failPhase=''
function Note($Message){}
function Save-Json($Name,$Value){}
function Get-State{return $script:fake.Clone()}
function Measure-Refs($Phase){$script:calls.Add($Phase);if($Phase -eq $script:failPhase){return @(@{reachable=$false;count=0},@{reachable=$false;count=0})};return $good}
function Query-Time($Phase){return @{source='time.windows.com,0x9';source_exit=0;status_exit=0}}
function Native($Exe,$ArgList,$Seconds,$Name){$script:calls.Add($Name);return @{exit=0}}
function Start-Time{$script:calls.Add('start');$script:fake.state='Running'}
function Stop-Time{$script:calls.Add('stop');$script:fake.state='Stopped'}
function Start-Sleep{}
$script:status=@{result='INCOMPLETE';clock_correction_attempted=$false}
Invoke-Repair $s $m
Assert ($script:status.result -eq 'WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED' -and $script:fake.state -eq 'Running' -and $script:fake.start -eq 3) 'success preserves startup'
Assert ($script:calls.IndexOf('start') -lt $script:calls.IndexOf('resync')) 'order'
Restore-State $s;Assert ($script:fake.state -eq 'Stopped') 'rollback'
$script:fake=$s.Clone();$script:changed=$false;$script:failPhase='before';$script:calls.Clear()
Reject {Invoke-Repair $s $m} 'NTP_REFERENCE_UNAVAILABLE'
Assert (-not $script:changed -and -not $script:calls.Contains('start')) 'no mutation when unreachable'
$script:failPhase='';$good[1].median_s=1.0
Reject {Invoke-Repair $s $m} 'REFERENCE_DISAGREEMENT_OR_LARGE_OFFSET'
Assert (-not $script:changed) 'no mutation on reference disagreement'
$good[1].median_s=-.02
$script:failPhase='after-2';$script:status=@{result='INCOMPLETE';clock_correction_attempted=$false}
Reject {Invoke-Repair $s $m} 'FINAL_SYNC_VERIFICATION_FAILED'
Restore-State $s;Assert ($script:fake.state -eq 'Stopped') 'failure rollback'
$script:fake=$s.Clone();$script:fake.state='Running';$s=$script:fake.Clone();$script:failPhase='';$script:calls.Clear();$script:changed=$false
Invoke-Repair $s $m;Assert (-not $script:calls.Contains('resync') -and -not $script:changed) 'healthy no change'
Write-Host 'WINDOWS_RECOVERY_MOCK_QA_PASS; NO REAL MUTATION'
