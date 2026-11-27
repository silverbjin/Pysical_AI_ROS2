param([string]$RunnerPath=(Join-Path $PSScriptRoot '../scripts/clock_diag_windows_recovery.ps1'))
$ErrorActionPreference='Stop'
. $RunnerPath -LibraryOnly
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
$ko=[regex]::Unescape('\uc724\ucd08 \uc870\uc815: 3(\ub3d9\uae30\ud654\ub418\uc9c0 \uc54a\uc74c)\n\uacc4\uce35: 0(\uc9c0\uc815\ub418\uc9c0 \uc54a\uc74c)\n\ucc38\uc870 ID: 0x00000000(\uc9c0\uc815\ub418\uc9c0 \uc54a\uc74c)\n\ub9c8\uc9c0\ub9c9 \ub3d9\uae30\ud654 \uc624\ub958: 1 (\uc0ac\uc6a9 \uac00\ub2a5\ud55c \uc2dc\uac04 \ub370\uc774\ud130\uac00 \uc5c6\uc5b4 \ucef4\ud4e8\ud130\uac00 \ub3d9\uae30\ud654\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.)\n\ub9c8\uc9c0\ub9c9\uc73c\ub85c \ub3d9\uae30\ud654\ud55c \ud6c4 \uc9c0\ub09c \uc2dc\uac04: 47.7481348s')
$badSync=Parse-SyncStatus $ko
Assert ($badSync.leap -eq 3 -and $badSync.stratum -eq 0 -and $badSync.last_error -eq 1 -and -not $badSync.healthy) 'actual Korean RED status rejected despite exit zero'
$en=@('Leap Indicator: 0(no warning)','Stratum: 5','ReferenceId: 0xB7731234','Last Sync Error: 0 (The command completed successfully.)','Time since Last Good Sync Time: 45.2s') -join [Environment]::NewLine
Assert ((Parse-SyncStatus $en).healthy) 'English synced status'
Assert (-not (Parse-SyncStatus ($en.Replace('45.2s','3601s'))).healthy) 'reject stale sync'
Assert (-not (Parse-SyncStatus 'Leap Indicator: 0').healthy) 'missing fields fail closed'
Assert (-not (Check-Sync @{source='time.windows.com,0x9';source_exit=0;status_exit=0;sync=$badSync} $s)) 'configured source is not proof of sync'
$script:fake=$s.Clone();$script:calls=New-Object 'System.Collections.Generic.List[string]';$script:failPhase=''
function Note($Message){}
function Save-Json($Name,$Value){}
function Get-State{return $script:fake.Clone()}
function Measure-Refs($Phase){$script:calls.Add($Phase);if($Phase -eq $script:failPhase){return @(@{reachable=$false;count=0},@{reachable=$false;count=0})};return $good}
function Query-Time($Phase){return @{source='time.windows.com,0x9';source_exit=0;status_exit=0;sync=@{healthy=$true}}}
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
$script:status=@{result='INCOMPLETE';clock_correction_attempted=$false};$script:calls.Clear()
Invoke-VerifyOnly $s
Assert ($script:status.result -eq 'WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED' -and -not $script:calls.Contains('resync') -and -not $script:calls.Contains('start')) 'readonly healthy no mutations'
function Query-Time($Phase){return @{source='time.windows.com,0x9';source_exit=0;status_exit=0;sync=@{healthy=$false}}}
$script:status=@{result='INCOMPLETE';clock_correction_attempted=$false};$script:calls.Clear()
Invoke-VerifyOnly $s
Assert ($script:status.result -eq 'WINDOWS_TIME_SYNC_HOLD' -and -not $script:calls.Contains('resync') -and -not $script:calls.Contains('start')) 'readonly contradictory status HOLD'
Reject {Invoke-Repair $s $m} 'ACCURATE_CLOCK_SYNC_STATE_UNCONFIRMED'
Write-Host 'WINDOWS_RECOVERY_MOCK_QA_PASS; NO REAL MUTATION'

# Exercise the exact production finalizer with real files, ZIP, manifest and SHA256.
# Re-load original functions to remove orchestration mocks. No service APIs invoked.
. $RunnerPath -LibraryOnly
function Test-Finalizer([string]$Case,[string]$Result,[bool]$ReadOnly,[bool]$ExpectComplete,[bool]$WithError=$false,[bool]$WithFinalStateError=$false,[bool]$Changed=$false) {
    $base=Join-Path ([IO.Path]::GetTempPath()) ('ch15-finalizer-'+[Guid]::NewGuid().ToString('N'))
    $script:root=$base
    New-Item -ItemType Directory -Path $base | Out-Null
    try {
        $script:changed=$Changed
        $script:status=@{result=$Result;verify_only=$ReadOnly;clock_correction_attempted=$false;rollback='NOT_NEEDED';owner_environment_acceptance=$false}
        if($WithError){$script:status.error='fixture query exception'}
        if($WithFinalStateError){$script:status.final_state_error='fixture final query exception'}
        Save-Json 'verify-summary.json' @(@{phase='verify-1';sync_pass=$false},@{phase='verify-2';sync_pass=$false})
        $caught=$false
        try {Complete-Run} catch {if($_.Exception.Message -notmatch 'WINDOWS_TIME_EXECUTION_INCOMPLETE'){throw};$caught=$true}
        Assert ($caught -eq (-not $ExpectComplete)) "$Case exception contract"
        $zip=$base+'.zip'
        Assert ((Test-Path $zip) -and (Test-Path ($zip+'.sha256'))) "$Case archive exists"
        $expected=((Get-Content -LiteralPath ($zip+'.sha256') -Raw) -split '\s+')[0]
        Assert ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant() -eq $expected) "$Case outer hash"
        $unpack=$base+'-unpack'
        Expand-Archive -LiteralPath $zip -DestinationPath $unpack
        $saved=Get-Content (Join-Path $unpack 'status.json') -Raw | ConvertFrom-Json
        $expectedExecution=if($ExpectComplete){'COMPLETE'}else{'INCOMPLETE'}
        $expectedAcceptance=if($ExpectComplete -and $Result -eq 'WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED'){'CANDIDATE_REVIEW_REQUIRED'}else{'HOLD'}
        Assert ($saved.execution_status -eq $expectedExecution -and $saved.acceptance_status -eq $expectedAcceptance -and $saved.owner_environment_acceptance -eq $false) "$Case persisted decision"
        if($ExpectComplete){Assert ($saved.result -eq $Result) "$Case result preserved"}
        else{Assert ($saved.result -eq 'WINDOWS_TIME_INCOMPLETE') "$Case incomplete persisted"}
        $lines=@(Get-Content (Join-Path $unpack 'manifest.sha256'))
        Assert ($lines.Count -eq 2) "$Case manifest count"
        foreach($line in $lines){
            $parts=$line -split '  ',2
            Assert ((Get-FileHash -LiteralPath (Join-Path $unpack $parts[1]) -Algorithm SHA256).Hash.ToLowerInvariant() -eq $parts[0]) "$Case member $($parts[1])"
        }
    } finally {
        Remove-Item -LiteralPath $base,($base+'.zip'),($base+'.zip.sha256'),($base+'-unpack') -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Test-Finalizer 'owner-readonly-hold' 'WINDOWS_TIME_SYNC_HOLD' $true $true
Test-Finalizer 'readonly-candidate' 'WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED' $true $true
Test-Finalizer 'repair-candidate' 'WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED' $false $true
Test-Finalizer 'repair-hold-not-normal' 'WINDOWS_TIME_SYNC_HOLD' $false $false
Test-Finalizer 'query-exception' 'WINDOWS_TIME_INCOMPLETE' $true $false $true
Test-Finalizer 'hold-with-query-error' 'WINDOWS_TIME_SYNC_HOLD' $true $false $true
Test-Finalizer 'candidate-with-final-state-error' 'WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED' $true $false $false $true
Test-Finalizer 'readonly-hold-with-mutation' 'WINDOWS_TIME_SYNC_HOLD' $true $false $false $false $true
# Simulate archive failure, must not announce success or return normally.
$script:status=@{result='WINDOWS_TIME_SYNC_HOLD';verify_only=$true;rollback='NOT_NEEDED';clock_correction_attempted=$false}
$script:changed=$false
function Pack {throw 'FIXTURE_PACK_FAILED'}
Reject {Complete-Run} 'FIXTURE_PACK_FAILED'
Write-Host 'FINALIZER_ARCHIVE_AND_EXIT_QA_PASS'

# Single-variable poll experiment: exact production lifecycle, real archive/finalizer.
. $RunnerPath -LibraryOnly
function Poll-FixtureSnapshot([string]$Peer,[string]$Other='fixed',[string]$Trigger='same') {
    return @{state=@{state='Running';start=3;delayed=$null;type='NTP';peers=$Peer;ntp_enabled=1};other_json=$Other;peer_kind='String';trigger=$Trigger;qc='same'}
}
$a=Poll-FixtureSnapshot 'time.windows.com,0x9'
$b=Poll-FixtureSnapshot 'time.windows.com,0x8'
Assert (Same-PollSnapshot $a $b 'time.windows.com,0x8') 'poll exact single variable'
Assert (-not (Same-PollSnapshot $a (Poll-FixtureSnapshot 'time.windows.com,0x8' 'changed') 'time.windows.com,0x8')) 'poll rejects other registry change'
Assert (-not (Same-PollSnapshot $a (Poll-FixtureSnapshot 'time.windows.com,0x8' 'fixed' 'changed') 'time.windows.com,0x8')) 'poll rejects trigger change'
$b.state.start=2
Assert (-not (Same-PollSnapshot $a $b 'time.windows.com,0x8')) 'poll rejects startup change'
function Poll-FixtureQuery([bool]$Healthy,[double]$Age) {
    $leap=if($Healthy){0}else{3}
    $stratum=if($Healthy){5}else{0}
    $err=if($Healthy){0}else{1}
    $ref=if($Healthy){'0xB7731234'}else{'0x00000000'}
    return @{source='time.windows.com,0x8';source_exit=0;status_exit=0;sync=@{healthy=$Healthy;leap=$leap;stratum=$stratum;last_error=$err;reference_id=$ref;age_s=$Age}}
}
Assert (Test-FreshPoll (Poll-FixtureQuery $false 720) (Poll-FixtureQuery $true 3) 100 101 106) 'poll fresh age reset'
Assert (-not (Test-FreshPoll (Poll-FixtureQuery $false 720) (Poll-FixtureQuery $true 725) 100 101 106)) 'poll rejects stale healthy status'
Assert (-not (Test-FreshPoll (Poll-FixtureQuery $false 1) (Poll-FixtureQuery $true 1) 100 101 101)) 'poll rejects ambiguous age reset'
Assert (-not (Test-FreshPoll (Poll-FixtureQuery $false 720) (Poll-FixtureQuery $true 3) 100 101 99)) 'poll rejects invalid QPC'
# Fixture overrides only hardware/network dependencies. Real lifecycle, ZIP and manual rollback.
function Get-State {return (Poll-FixtureSnapshot $script:peer).state}
function Get-Management {
    $managed=($script:case -eq 'managed')
    return @{domain=$managed;policy=$false;mdm_policy=$false;mdm_url=$false;enrollment=$false;identity=@{AzureAdJoined='NO';EnterpriseJoined='NO';DomainJoined='NO';WorkplaceJoined='NO'}}
}
function Write-Backup($Original) {
    $script:calls.Add('backup')
    Save-Json 'before-state.json' $Original
    Set-Content -LiteralPath (Join-Path $script:root 'w32time-before.reg') -Value 'fixture backup'
}
function Get-PollSnapshot($Phase) {
    $other=if($script:case -eq 'config-drift' -and $script:peer -eq 'time.windows.com,0x8'){'changed'}else{'fixed'}
    $snap=Poll-FixtureSnapshot $script:peer $other
    Save-Json ($Phase+'-snapshot.json') $snap
    return $snap
}
function Measure-Refs($Phase) {
    $script:calls.Add($Phase)
    if($script:case -eq 'reference-fail' -or ($script:case -eq 'post-fail' -and $Phase -eq 'poll-after-2')){
        return @(@{reachable=$false;count=0},@{reachable=$false;count=0})
    }
    return @(@{reachable=$true;count=5;median_s=.015;max_abs_s=.016},@{reachable=$true;count=5;median_s=.014;max_abs_s=.017})
}
function Query-Time($Phase) {
    $script:clock+=1
    $script:calls.Add($Phase)
    if($Phase -eq 'poll-before'){
        if($script:case -eq 'already-healthy'){return (Poll-FixtureQuery $true 15)}
        return (Poll-FixtureQuery $false 720)
    }
    if($script:case -in @('no-sync','rollback-fail')){return (Poll-FixtureQuery $false 720)}
    if($script:case -eq 'stale-sync'){return (Poll-FixtureQuery $true 720)}
    return (Poll-FixtureQuery $true 1)
}
function Poll-Now {return $script:clock}
function Poll-Wait($Seconds){$script:clock+=$Seconds}
function Native($Exe,$ArgList,$Seconds,$Name) {
    $script:calls.Add($Name)
    if($Exe -ne 'w32tm.exe'){throw 'UNEXPECTED_NATIVE_FIXTURE_CALL'}
    if($Name -in @('apply-peer','rollback-peer')){
        Assert ($ArgList.Count -eq 3 -and $ArgList[0] -eq '/config' -and $ArgList[2] -eq '/update') "$Name exact arguments"
        if($Name -eq 'apply-peer'){
            Assert ((Test-Path (Join-Path $script:root 'manual-rollback.txt')) -and $script:calls.Contains('backup')) 'backup before apply'
            $script:peer='time.windows.com,0x8'
            if($script:case -eq 'apply-partial'){return @{exit=1}}
            if($script:case -eq 'unexpected-peer'){$script:peer='other.invalid,0x8'}
        }else{
            if($script:case -eq 'rollback-fail'){return @{exit=1}}
            $script:peer='time.windows.com,0x9'
        }
        return @{exit=0}
    }
    if($Name -eq 'poll-resync'){return @{exit=0;stdout='no time data fixture'}}
    throw 'UNEXPECTED_NATIVE_NAME'
}
# No actual service/event query in fixture; real archive still exercised.
function Get-WinEvent {return @()}
function Test-PollLifecycle($Case,$Expected,$ExpectedRollback,$ExpectedPeer,[bool]$ExpectThrow=$false) {
    $script:case=$Case;$script:peer='time.windows.com,0x9';$script:clock=100.0
    if($Case -eq 'unexpected-initial-peer'){$script:peer='time.windows.com,0x8'}
    $script:calls=New-Object 'System.Collections.Generic.List[string]'
    $script:changed=$false
    $base=Join-Path ([IO.Path]::GetTempPath()) ('ch15-poll-'+[Guid]::NewGuid().ToString('N'))
    $script:root=$base
    New-Item -ItemType Directory -Path $base|Out-Null
    $script:status=@{result='WINDOWS_TIME_INCOMPLETE';rollback='NOT_NEEDED';clock_correction_attempted=$false;owner_environment_acceptance=$false}
    try{
        $caught=$false
        try{Invoke-PollLifecycle}catch{if($_.Exception.Message -notmatch 'WINDOWS_POLL_EXECUTION_INCOMPLETE'){throw};$caught=$true}
        Assert ($caught -eq $ExpectThrow) "$Case terminal exception"
        Assert ($script:peer -eq $ExpectedPeer) "$Case final peer"
        Assert (@($script:calls|Where-Object {$_ -eq 'poll-resync'}).Count -le 1) "$Case bounded resync"
        if($Case -in @('managed','already-healthy','reference-fail','unexpected-initial-peer')){Assert (-not $script:calls.Contains('apply-peer')) "$Case no change"}
        $zip=$base+'.zip'
        Assert (Test-Path $zip) "$Case archive"
        $expectedHash=((Get-Content ($zip+'.sha256') -Raw)-split '\s+')[0]
        Assert ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant() -eq $expectedHash) "$Case archive hash"
        $dest=$base+'-unpack';Expand-Archive $zip -DestinationPath $dest
        $saved=Get-Content (Join-Path $dest 'status.json') -Raw|ConvertFrom-Json
        Assert ($saved.result -eq $Expected -and $saved.rollback -eq $ExpectedRollback -and -not $saved.owner_environment_acceptance) "$Case persisted decision"
        $expectedExec=if($ExpectThrow){'INCOMPLETE'}else{'COMPLETE'}
        Assert ($saved.execution_status -eq $expectedExec) "$Case execution state"
        foreach($line in (Get-Content (Join-Path $dest 'manifest.sha256'))){
            $parts=$line -split '  ',2
            Assert ((Get-FileHash (Join-Path $dest $parts[1]) -Algorithm SHA256).Hash.ToLowerInvariant() -eq $parts[0]) "$Case member $($parts[1])"
        }
    }finally{
        Remove-Item -LiteralPath $base,($base+'.zip'),($base+'.zip.sha256'),($base+'-unpack') -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Test-PollLifecycle 'success' 'WINDOWS_POLL_CHANGE_CANDIDATE_REVIEW_REQUIRED' 'NOT_NEEDED' 'time.windows.com,0x8'
Test-PollLifecycle 'no-sync' 'WINDOWS_POLL_CHANGE_HOLD' 'VERIFIED' 'time.windows.com,0x9'
Test-PollLifecycle 'stale-sync' 'WINDOWS_POLL_CHANGE_HOLD' 'VERIFIED' 'time.windows.com,0x9'
Test-PollLifecycle 'post-fail' 'WINDOWS_POLL_CHANGE_HOLD' 'VERIFIED' 'time.windows.com,0x9'
Test-PollLifecycle 'config-drift' 'WINDOWS_POLL_CHANGE_HOLD' 'VERIFIED' 'time.windows.com,0x9'
Test-PollLifecycle 'managed' 'WINDOWS_POLL_CHANGE_HOLD' 'NOT_NEEDED' 'time.windows.com,0x9'
Test-PollLifecycle 'reference-fail' 'WINDOWS_POLL_CHANGE_HOLD' 'NOT_NEEDED' 'time.windows.com,0x9'
Test-PollLifecycle 'already-healthy' 'WINDOWS_POLL_CHANGE_HOLD' 'NOT_NEEDED' 'time.windows.com,0x9'
Test-PollLifecycle 'unexpected-initial-peer' 'WINDOWS_POLL_CHANGE_HOLD' 'NOT_NEEDED' 'time.windows.com,0x8'
Test-PollLifecycle 'apply-partial' 'WINDOWS_POLL_CHANGE_INCOMPLETE' 'VERIFIED' 'time.windows.com,0x9' $true
Test-PollLifecycle 'rollback-fail' 'WINDOWS_POLL_CHANGE_INCOMPLETE' 'FAILED_OR_UNVERIFIED' 'time.windows.com,0x8' $true
Test-PollLifecycle 'unexpected-peer' 'WINDOWS_POLL_CHANGE_INCOMPLETE' 'FAILED_OR_UNVERIFIED' 'other.invalid,0x8' $true
# A real pack failure after successful candidate must rollback.
$script:case='success';$script:peer='time.windows.com,0x9';$script:clock=100.0;$script:changed=$false
$script:calls=New-Object 'System.Collections.Generic.List[string]'
$script:root=Join-Path ([IO.Path]::GetTempPath()) ('ch15-poll-pack-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $script:root|Out-Null
$script:status=@{result='WINDOWS_TIME_INCOMPLETE';rollback='NOT_NEEDED';clock_correction_attempted=$false;owner_environment_acceptance=$false}
function Pack {throw 'FIXTURE_ARCHIVE_FAILURE'}
try{
    Reject {Invoke-PollLifecycle} 'POLL_EVIDENCE_PACK_FAILED'
    Assert ($script:peer -eq 'time.windows.com,0x9' -and $script:status.rollback -eq 'VERIFIED' -and $script:status.execution_status -eq 'INCOMPLETE') 'pack failure rollback'
}finally{Remove-Item -LiteralPath $script:root -Recurse -Force}
Write-Host 'POLL_LIFECYCLE_QA_PASS; NO REAL TIME MUTATION'
