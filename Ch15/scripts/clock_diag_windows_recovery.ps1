[CmdletBinding()]
param([switch]$LibraryOnly,[switch]$VerifyOnly,[switch]$Approved,[switch]$PollChangeApproved,[string]$SourcePin,[string]$SourceSha256,
      [string]$OutputRoot=(Join-Path $HOME 'ch15-windows-time-evidence'))
$ErrorActionPreference='Stop'
$script:root=$null
$script:utf8=New-Object System.Text.UTF8Encoding($false)
$script:changed=$false
$script:status=$null
function Save-Json($Name,$Value) {
    [IO.File]::WriteAllText((Join-Path $script:root $Name),($Value|ConvertTo-Json -Depth 10),$script:utf8)
}
function Note([string]$Message) {
    Write-Host $Message
    [IO.File]::AppendAllText((Join-Path $script:root 'progress.log'),("$([Diagnostics.Stopwatch]::GetTimestamp()) $Message"+[Environment]::NewLine),$script:utf8)
}
function Native([string]$Exe,[string[]]$ArgList,[int]$Seconds,[string]$Name) {
    $psi=New-Object Diagnostics.ProcessStartInfo
    $psi.FileName=Join-Path $env:SystemRoot ('System32\'+$Exe)
    $psi.Arguments=$ArgList -join ' '
    $psi.UseShellExecute=$false; $psi.RedirectStandardOutput=$true; $psi.RedirectStandardError=$true; $psi.CreateNoWindow=$true
    $p=New-Object Diagnostics.Process
    $p.StartInfo=$psi
    try {
        if (-not $p.Start()) { throw 'NATIVE_START_FAILED' }
        $o=$p.StandardOutput.ReadToEndAsync(); $e=$p.StandardError.ReadToEndAsync()
        if (-not $p.WaitForExit($Seconds*1000)) {
            $p.Kill(); [void]$p.WaitForExit(5000)
            $r=@{exit=-1;stdout='';stderr='TIMEOUT'}
        } else {
            $r=@{exit=$p.ExitCode;stdout=$o.GetAwaiter().GetResult();stderr=$e.GetAwaiter().GetResult()}
        }
        Save-Json ($Name+'.json') $r
        return $r
    } finally { $p.Dispose() }
}
function Require-Ok($R,$Label) { if ($R.exit -ne 0) { throw "$Label exit=$($R.exit)" } }
function Get-State {
    $k='HKLM:\SYSTEM\CurrentControlSet\Services\W32Time'
    $base=Get-ItemProperty -LiteralPath $k
    $par=Get-ItemProperty -LiteralPath ($k+'\Parameters')
    $ntp=Get-ItemProperty -LiteralPath ($k+'\TimeProviders\NtpClient')
    $d=$null
    if ($base.PSObject.Properties['DelayedAutoStart']) { $d=[int]$base.DelayedAutoStart }
    return @{state=(Get-Service W32Time).Status.ToString(); start=[int]$base.Start; delayed=$d; type=[string]$par.Type; peers=[string]$par.NtpServer; ntp_enabled=[int]$ntp.Enabled}
}
function Get-Management {
    $cs=Get-CimInstance Win32_ComputerSystem
    $ds=Native 'dsregcmd.exe' @('/status') 30 'dsreg-status'
    Require-Ok $ds 'IDENTITY_QUERY_FAILED'
    $fields=@{}
    foreach($field in @('AzureAdJoined','EnterpriseJoined','DomainJoined','WorkplaceJoined')) {
        $m=[regex]::Match($ds.stdout,('(?im)^\s*'+$field+'\s*:\s*(YES|NO)\s*$'))
        $fields[$field]=if($m.Success){$m.Groups[1].Value}else{'UNKNOWN'}
    }
    $enrolled=$false
    $ek='HKLM:\SOFTWARE\Microsoft\Enrollments'
    if(Test-Path $ek) {
        foreach($k in (Get-ChildItem -LiteralPath $ek)) {
            $v=Get-ItemProperty -LiteralPath $k.PSPath
            if($v.PSObject.Properties['EnrollmentState'] -and $v.EnrollmentState -eq 1 -and
              (($v.PSObject.Properties['ProviderID'] -and $v.ProviderID) -or ($v.PSObject.Properties['DiscoveryServiceFullURL'] -and $v.DiscoveryServiceFullURL))) {$enrolled=$true}
        }
    }
    return @{domain=[bool]$cs.PartOfDomain; identity=$fields;
      mdm_url=([regex]::IsMatch($ds.stdout,'(?im)^[ \t]*MdmUrl[ \t]*:[ \t]*\S+')); enrollment=$enrolled;
      policy=(Test-Path 'HKLM:\SOFTWARE\Policies\Microsoft\W32Time');
      mdm_policy=(Test-Path 'HKLM:\SOFTWARE\Microsoft\PolicyManager\current\device\ADMX_W32Time')}
}
function Get-Peers($State) {
    $peers=@()
    foreach($entry in ($State.peers -split '\s+')) {
        if(-not $entry){continue}
        if($entry -notmatch '^[A-Za-z0-9][A-Za-z0-9.-]*(?:,0x[0-9a-fA-F]+)?$'){throw 'UNSUPPORTED_PEER_FORMAT'}
        $peers+=($entry -split ',')[0].ToLowerInvariant()
    }
    if($peers.Count -eq 0){throw 'NO_CONFIGURED_PEERS'}
    return $peers
}
function Check-Preflight($S,$M) {
    if($M.domain -or $M.policy -or $M.mdm_policy -or $M.mdm_url -or $M.enrollment){throw 'MANAGED_OR_UNKNOWN_NO_CHANGE'}
    foreach($k in @('AzureAdJoined','EnterpriseJoined','DomainJoined','WorkplaceJoined')){
        if($M.identity[$k] -ne 'NO'){throw 'MANAGED_OR_UNKNOWN_NO_CHANGE'}
    }
    if($S.state -notin @('Running','Stopped') -or $S.start -notin @(2,3) -or $S.type -ne 'NTP' -or $S.ntp_enabled -ne 1){throw 'UNSUPPORTED_CONFIG_NO_CHANGE'}
    # No startup-type change: preserve native trigger policy, including Manual.
    [void](Get-Peers $S)
}
function Parse-Offsets([string]$Text) {
    $values=@()
    foreach($line in ($Text -split '\r?\n')) {
        if($line -match '(?i)([+-]\d+(?:[.,]\d+)?)\s*s\s*$'){
            $values+=[double]::Parse($Matches[1].Replace(',','.'),[Globalization.CultureInfo]::InvariantCulture)
        }
    }
    return $values
}
function Measure-Refs([string]$Phase) {
    $rows=@()
    foreach($server in @('time.windows.com','time.cloudflare.com')){
        $r=Native 'w32tm.exe' @('/stripchart',"/computer:$server",'/dataonly','/samples:5','/period:1') 40 ($Phase+'-'+$server)
        $v=@(Parse-Offsets $r.stdout);$med=$null;$max=$null
        if($v.Count){
            $sorted=@($v|Sort-Object);$mid=[int][Math]::Floor($v.Count/2)
            if($v.Count%2){$med=$sorted[$mid]}else{$med=($sorted[$mid-1]+$sorted[$mid])/2}
            $max=($v|ForEach-Object{[Math]::Abs($_)}|Measure-Object -Maximum).Maximum
        }
        $rows+=@{host=$server;count=$v.Count;values_s=$v;median_s=$med;max_abs_s=$max;reachable=($r.exit -eq 0 -and $v.Count -ge 4)}
    }
    Save-Json ($Phase+'-offsets.json') $rows
    return $rows
}
function Check-Offsets($Rows,[switch]$ReachableOnly) {
    if(@($Rows).Count -ne 2){return $false}
    foreach($x in $Rows){
        if(-not $x.reachable -or $x.count -lt 4){return $false}
        if(-not $ReachableOnly -and ([Math]::Abs($x.median_s) -gt .1 -or $x.max_abs_s -gt .2)){return $false}
    }
    return $true
}
function Parse-SyncStatus([string]$Text) {
    # Match numeric fields, not translated success words. ASCII regex escapes for PS 5.1 raw UTF-8.
    $fields=@{leap='Leap Indicator|\uc724\ucd08 \uc870\uc815';stratum='Stratum|\uacc4\uce35';last_error='Last Sync Error|\ub9c8\uc9c0\ub9c9 \ub3d9\uae30\ud654 \uc624\ub958'}
    $r=@{leap=$null;stratum=$null;last_error=$null;reference_id=$null;age_s=$null;last_sync_text=$null;healthy=$false}
    foreach($k in $fields.Keys){
        $m=[regex]::Matches($Text,('(?im)^[ \t]*(?:'+$fields[$k]+')[ \t]*:[ \t]*(\d+)\b'))
        if($m.Count -eq 1){$r[$k]=[long]$m[0].Groups[1].Value}
    }
    $m=[regex]::Matches($Text,'(?im)^[ \t]*(?:ReferenceId|Reference ID|\ucc38\uc870 ID)[ \t]*:[ \t]*(0x[0-9a-f]{8})\b')
    if($m.Count -eq 1){$r.reference_id=$m[0].Groups[1].Value.ToLowerInvariant()}
    $m=[regex]::Matches($Text,'(?im)^[ \t]*(?:Time since Last Good Sync Time|\ub9c8\uc9c0\ub9c9\uc73c\ub85c \ub3d9\uae30\ud654\ud55c \ud6c4 \uc9c0\ub09c \uc2dc\uac04)[ \t]*:[ \t]*(\d+(?:[.,]\d+)?)[ \t]*s\b')
    if($m.Count -eq 1){$r.age_s=[double]::Parse($m[0].Groups[1].Value.Replace(',','.'),[Globalization.CultureInfo]::InvariantCulture)}
    $m=[regex]::Matches($Text,'(?im)^[ \t]*(?:Last Successful Sync Time|\ub9c8\uc9c0\ub9c9\uc73c\ub85c \ub3d9\uae30\ud654\ud55c \uc2dc\uac04)[ \t]*:[ \t]*([^\r\n]+)')
    if($m.Count -eq 1){$r.last_sync_text=$m[0].Groups[1].Value.Trim()}
    $r.healthy=($null -ne $r.leap -and $r.leap -in @(0,1,2) -and $null -ne $r.stratum -and $r.stratum -ge 1 -and $r.stratum -le 15 -and $null -ne $r.last_error -and $r.last_error -eq 0 -and $null -ne $r.reference_id -and $r.reference_id -ne '0x00000000' -and $null -ne $r.age_s -and $r.age_s -le 3600)
    return $r
}
function Check-Sync($Q,$S) {
    return ((Check-Source $Q $S) -and $null -ne $Q.sync -and $Q.sync.healthy -eq $true)
}
function Invoke-VerifyOnly($Original) {
    Note 'READ_ONLY_NO_SERVICE_OR_CLOCK_MUTATION'
    $results=@()
    foreach($phase in @('verify-1','verify-2')){
        if($phase -eq 'verify-2'){Note 'VERIFY_WINDOW_2_AFTER_30S';Start-Sleep -Seconds 30}
        $rows=@(Measure-Refs $phase)
        $q=Query-Time $phase
        $s=Get-State
        $row=@{phase=$phase;offsets_pass=(Check-Offsets $rows);sync_pass=(Check-Sync $q $Original);state=$s.state;config_unchanged=(Same-Config $s $Original)}
        $reasons=@()
        if(-not $row.offsets_pass){$reasons+='EXTERNAL_OFFSET_OR_COVERAGE'}
        if(-not $row.sync_pass){$reasons+='W32TIME_SYNC_OR_SOURCE'}
        if($row.state -ne 'Running'){$reasons+='SERVICE_NOT_RUNNING'}
        if(-not $row.config_unchanged){$reasons+='CONFIG_CHANGED'}
        $row.reasons=$reasons
        $results+=$row
        Note ("WINDOW_RESULT="+$phase+" reasons="+($reasons -join ','))
    }
    Save-Json 'verify-summary.json' $results
    if(@($results|Where-Object {-not $_.offsets_pass -or -not $_.sync_pass -or $_.state -ne 'Running' -or -not $_.config_unchanged}).Count -eq 0){
        $script:status.result='WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED'
    }else{$script:status.result='WINDOWS_TIME_SYNC_HOLD'}
}
function Query-Time([string]$Phase) {
    $s=Native 'w32tm.exe' @('/query','/source') 15 ($Phase+'-source')
    $t=Native 'w32tm.exe' @('/query','/status','/verbose') 15 ($Phase+'-status')
    [void](Native 'w32tm.exe' @('/query','/configuration') 15 ($Phase+'-configuration'))
    [void](Native 'w32tm.exe' @('/query','/peers') 15 ($Phase+'-peers'))
    $sync=Parse-SyncStatus $t.stdout
    Save-Json ($Phase+'-sync-fields.json') $sync
    return @{source=$s.stdout.Trim();source_exit=$s.exit;status_exit=$t.exit;sync=$sync}
}
function Check-Source($Q,$S) {
    if($Q.source_exit -ne 0 -or $Q.status_exit -ne 0){return $false}
    return ((($Q.source -split ',')[0].Trim().ToLowerInvariant()) -in @(Get-Peers $S))
}
function Same-Config($A,$B) {
    return ($A.start -eq $B.start -and $A.delayed -eq $B.delayed -and $A.type -ceq $B.type -and $A.peers -ceq $B.peers -and $A.ntp_enabled -eq $B.ntp_enabled)
}
function Start-Time {
    if ((Get-Service W32Time).Status -ne 'Running') { Require-Ok (Native 'sc.exe' @('start','W32Time') 25 'start-service') 'START_FAILED' }
    (Get-Service W32Time).WaitForStatus('Running',[TimeSpan]::FromSeconds(20))
}
function Stop-Time {
    if ((Get-Service W32Time).Status -ne 'Stopped') { Require-Ok (Native 'sc.exe' @('stop','W32Time') 25 'rollback-stop-service') 'STOP_FAILED' }
    (Get-Service W32Time).WaitForStatus('Stopped',[TimeSpan]::FromSeconds(20))
}
function Restore-State($Original) {
    $s=Get-State
    if(-not (Same-Config $s $Original)){throw 'EXTERNAL_CONFIG_CHANGE_MANUAL_REVIEW'}
    if($Original.state -eq 'Stopped' -and $s.state -ne 'Stopped'){Stop-Time}
    $after=Get-State
    Save-Json 'rollback-state.json' $after
    if($after.state -ne $Original.state -or -not (Same-Config $after $Original)){throw 'ROLLBACK_STATE_MISMATCH'}
}
function Invoke-Repair($Original,$Mgmt) {
    Check-Preflight $Original $Mgmt
    Note 'PRECHECK_PASS_MEASURE_EXTERNAL_NTP'
    $before=@(Measure-Refs 'before')
    if(-not (Check-Offsets $before -ReachableOnly)){throw 'NTP_REFERENCE_UNAVAILABLE_NO_CHANGE'}
    if ([Math]::Abs($before[0].median_s-$before[1].median_s) -gt .2 -or $before[0].max_abs_s -gt 30 -or $before[1].max_abs_s -gt 30) { throw 'REFERENCE_DISAGREEMENT_OR_LARGE_OFFSET_NO_CHANGE' }
    $q=Query-Time 'before'
    $healthy=($Original.state -eq 'Running' -and (Check-Sync $q $Original) -and (Check-Offsets $before))
    if($Original.state -eq 'Running' -and (Check-Offsets $before) -and -not $healthy){throw 'ACCURATE_CLOCK_SYNC_STATE_UNCONFIRMED_USE_VERIFYONLY'}
    if(-not $healthy){
        $script:status.clock_correction_attempted=$true
        if($Original.state -eq 'Stopped'){
            $script:changed=$true
            Note 'START_EXISTING_W32TIME'
            Start-Time
        }
        Note 'RESYNC_EXISTING_NTP_SOURCE'
        Require-Ok (Native 'w32tm.exe' @('/resync','/rediscover') 60 'resync') 'RESYNC_FAILED'
    }else{Note 'ALREADY_SYNCHRONIZED_NO_RESYNC'}
    Note 'VERIFY_WINDOW_1'
    $one=@(Measure-Refs 'after-1')
    if(-not (Check-Offsets $one) -or -not (Check-Sync (Query-Time 'after-1') $Original)){throw 'FIRST_SYNC_VERIFICATION_FAILED'}
    Note 'VERIFY_WINDOW_2_AFTER_30S'
    Start-Sleep -Seconds 30
    $two=@(Measure-Refs 'after-2');$s=Get-State
    Save-Json 'after-state.json' $s
    if(-not (Check-Offsets $two) -or -not (Check-Sync (Query-Time 'after-2') $Original) -or $s.state -ne 'Running' -or -not (Same-Config $s $Original)){throw 'FINAL_SYNC_VERIFICATION_FAILED'}
    $script:status.result='WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED'
}
function Write-Backup($Original) {
    Save-Json 'before-state.json' $Original
    $path=Join-Path $script:root 'w32time-before.reg'
    & reg.exe export 'HKLM\SYSTEM\CurrentControlSet\Services\W32Time' $path /y | Out-Null
    if($LASTEXITCODE -ne 0 -or -not (Test-Path $path)){throw 'REGISTRY_EXPORT_FAILED_NO_CHANGE'}
    Require-Ok (Native 'sc.exe' @('qc','W32Time') 15 'service-qc-before') 'SC_QC_FAILED'
    Require-Ok (Native 'sc.exe' @('qtriggerinfo','W32Time') 15 'service-triggers-before') 'SC_TRIGGER_QUERY_FAILED'
    $lines=@('# Elevated PowerShell: only if original service state needs restoration.','# Do not rewind the clock or import the registry backup blindly.')
    if($Original.state -eq 'Stopped'){$lines+='Stop-Service -Name W32Time'}else{$lines+='Start-Service -Name W32Time'}
    $lines+='Get-Service W32Time';$lines+='sc.exe qc W32Time'
    [IO.File]::WriteAllLines((Join-Path $script:root 'manual-rollback.txt'),[string[]]$lines,$script:utf8)
}
function Pack {
    Save-Json 'status.json' $script:status
    $manifest=@(Get-ChildItem $script:root -File -Recurse|Sort-Object FullName|ForEach-Object{
        $rel=$_.FullName.Substring($script:root.Length+1).Replace('\','/')
        ((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()+'  '+$rel)
    })
    [IO.File]::WriteAllLines((Join-Path $script:root 'manifest.sha256'),[string[]]$manifest,$script:utf8)
    $zip=$script:root+'.zip'
    Compress-Archive -Path (Join-Path $script:root '*') -DestinationPath $zip
    [IO.File]::WriteAllText($zip+'.sha256',((Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()+'  '+(Split-Path $zip -Leaf)+[Environment]::NewLine),$script:utf8)
    Write-Host "EVIDENCE=$zip";Write-Host "SHA256=$zip.sha256"
}
function Complete-Run {
    # A completed read-only observation may fail the environment gate.
    # Preserve genuine execution failures and never promote HOLD to acceptance.
    $candidate=($script:status.result -eq 'WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED')
    $hold=($script:status.result -eq 'WINDOWS_TIME_SYNC_HOLD' -and $script:status.verify_only -eq $true -and -not $script:changed -and -not $script:status.clock_correction_attempted -and $script:status.rollback -eq 'NOT_NEEDED')
    $complete=(($candidate -or $hold) -and -not $script:status.error -and -not $script:status.final_state_error)
    $script:status.execution_status=if($complete){'COMPLETE'}else{'INCOMPLETE'}
    $script:status.acceptance_status=if($complete -and $candidate){'CANDIDATE_REVIEW_REQUIRED'}else{'HOLD'}
    $script:status.owner_environment_acceptance=$false
    if(-not $complete){$script:status.result='WINDOWS_TIME_INCOMPLETE'}
    # Pack must succeed before announcing completion. Pack exceptions propagate.
    Pack
    Write-Host "EXECUTION_STATUS=$($script:status.execution_status)"
    Write-Host "ACCEPTANCE_STATUS=$($script:status.acceptance_status)"
    Write-Host $script:status.result
    Write-Host "ROLLBACK=$($script:status.rollback)"
    if(-not $complete){throw 'WINDOWS_TIME_EXECUTION_INCOMPLETE; review evidence (rollback only for repair mode)'}
    if($hold){Write-Host 'NEXT_ACTION=UPLOAD_EVIDENCE_FOR_REVIEW; NO_AUTOMATIC_RETRY; WSL2_GATE_HOLD'}
}
# R10 approved single-variable adaptive polling experiment.
$script:pollOld='time.windows.com,0x9'
$script:pollNew='time.windows.com,0x8'
function Poll-Now { return ([double][Diagnostics.Stopwatch]::GetTimestamp()/[Diagnostics.Stopwatch]::Frequency) }
function Poll-Wait([int]$Seconds) { Start-Sleep -Seconds $Seconds }
function Read-PollRegistry {
    $base='HKLM:\SYSTEM\CurrentControlSet\Services\W32Time'
    $rows=@()
    foreach($section in @('Config','Parameters','TimeProviders')){
        $path=Join-Path $base $section
        $keys=@(Get-Item -LiteralPath $path)+@(Get-ChildItem -LiteralPath $path -Recurse)
        foreach($key in ($keys|Sort-Object Name)){
            foreach($name in ($key.GetValueNames()|Sort-Object)){
                $v=$key.GetValue($name,$null,[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
                $rows+=[ordered]@{key=$key.Name;name=$name;kind=$key.GetValueKind($name).ToString();value_json=(ConvertTo-Json -InputObject $v -Compress -Depth 10)}
            }
        }
    }
    return $rows
}
function Get-PollSnapshot([string]$Phase) {
    $s=Get-State
    $rows=@(Read-PollRegistry)
    $tr=Native 'sc.exe' @('qtriggerinfo','W32Time') 15 ($Phase+'-trigger')
    $qc=Native 'sc.exe' @('qc','W32Time') 15 ($Phase+'-qc')
    Require-Ok $tr 'TRIGGER_QUERY_FAILED'
    Require-Ok $qc 'SERVICE_CONFIG_QUERY_FAILED'
    $peer=@($rows|Where-Object {$_.key -match '\\Parameters$' -and $_.name -eq 'NtpServer'})
    if($peer.Count -ne 1 -or ($peer[0].value_json|ConvertFrom-Json) -cne $s.peers){throw 'PEER_SNAPSHOT_INCONSISTENT'}
    $other=@($rows|Where-Object {-not ($_.key -match '\\Parameters$' -and $_.name -eq 'NtpServer')})
    $snap=@{state=$s;registry=$rows;other_json=(ConvertTo-Json -InputObject $other -Depth 10 -Compress);peer_kind=$peer[0].kind;trigger=$tr.stdout;qc=$qc.stdout}
    Save-Json ($Phase+'-snapshot.json') $snap
    return $snap
}
function Same-PollSnapshot($Original,$Actual,[string]$ExpectedPeer) {
    $a=$Original.state;$b=$Actual.state
    return ($b.peers -ceq $ExpectedPeer -and $a.state -eq $b.state -and $a.start -eq $b.start -and $a.delayed -eq $b.delayed -and $a.type -ceq $b.type -and $a.ntp_enabled -eq $b.ntp_enabled -and $Original.other_json -ceq $Actual.other_json -and $Original.peer_kind -ceq $Actual.peer_kind -and $Original.trigger -ceq $Actual.trigger -and $Original.qc -ceq $Actual.qc)
}
function Set-PollPeer([string]$Peer,[string]$Phase) {
    if($Peer -cnotin @($script:pollOld,$script:pollNew)){throw 'UNAPPROVED_PEER_CHANGE'}
    # Type already NTP. Omit /syncfromflags to avoid rewriting unrelated settings.
    return (Native 'w32tm.exe' @('/config',"/manualpeerlist:$Peer",'/update') 30 $Phase)
}
function Write-PollRollback {
    $lines=@(
        '# Elevated PowerShell. Use only if this experiment left 0x8 and rollback is needed.',
        '# Do not run if another administrator changed the peer or management policy.',
        '$p=(Get-ItemProperty -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Parameters").NtpServer',
        'if ($p -ne "time.windows.com,0x8") { throw "UNEXPECTED_PEER_NO_CHANGE" }',
        'w32tm.exe /config /manualpeerlist:time.windows.com,0x9 /update',
        'if ($LASTEXITCODE -ne 0) { throw "ROLLBACK_COMMAND_FAILED" }',
        '$p=(Get-ItemProperty -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Parameters").NtpServer',
        'if ($p -ne "time.windows.com,0x9") { throw "ROLLBACK_READBACK_FAILED" }',
        'w32tm.exe /query /configuration',
        '# No forced clock rewind, service restart or resync. Review full configuration against backup.'
    )
    [IO.File]::WriteAllLines((Join-Path $script:root 'manual-rollback.txt'),[string[]]$lines,$script:utf8)
}
function Restore-Poll($Original) {
    $script:status.rollback='FAILED_OR_UNVERIFIED'
    try {
        $mg=Get-Management
        Check-Preflight (Get-State) $mg
        $current=Get-PollSnapshot 'rollback-before'
        if($current.state.peers -ceq $script:pollNew){
            Require-Ok (Set-PollPeer $script:pollOld 'rollback-peer') 'ROLLBACK_COMMAND_FAILED'
        }elseif($current.state.peers -cne $script:pollOld){throw 'EXTERNAL_PEER_CHANGE_NO_OVERWRITE'}
        $after=Get-PollSnapshot 'rollback-after'
        if(-not (Same-PollSnapshot $Original $after $script:pollOld)){throw 'ROLLBACK_CONFIG_MISMATCH'}
        $script:status.rollback='VERIFIED'
        Note 'ORIGINAL_POLL_CONFIGURATION_RESTORED'
    }catch{
        $script:status.rollback_error=$_.Exception.Message
        Note ('ROLLBACK_UNVERIFIED '+$_.Exception.Message)
    }
}
function Has-PollFields($Q) {
    if($Q.source_exit -ne 0 -or $Q.status_exit -ne 0 -or $null -eq $Q.sync){return $false}
    foreach($k in @('leap','stratum','last_error','reference_id','age_s','last_sync_text')){
        if($null -eq $Q.sync[$k]){return $false}
    }
    return $true
}
function Test-FreshPoll($Before,$After,[double]$BeforeQpc,[double]$ChangeQpc,[double]$AfterQpc) {
    if(-not (Has-PollFields $Before) -or -not (Has-PollFields $After)){return $false}
    $elapsed=$AfterQpc-$BeforeQpc
    $sinceChange=$AfterQpc-$ChangeQpc
    if($elapsed -lt 0 -or $sinceChange -lt 0){return $false}
    # Require a different last-successful-sync timestamp and a sufficiently large age reset within the intervention window.
    # QPC is independent of wall-clock steps. No stale successful status reuse.
    return ($Before.sync.last_sync_text -cne $After.sync.last_sync_text -and $After.sync.age_s -ge 0 -and $After.sync.age_s -le ($sinceChange+2) -and ($Before.sync.age_s+$elapsed-$After.sync.age_s) -ge 3)
}
function Set-PollHold([string]$Reason) {
    $script:status.result='WINDOWS_POLL_CHANGE_HOLD'
    $script:status.hold_reason=$Reason
    Note ("POLL_HOLD="+$Reason)
}
function Invoke-PollExperiment($Original,$Mgmt) {
    try{Check-Preflight $Original.state $Mgmt}
    catch{Set-PollHold $_.Exception.Message;return}
    if($Original.state.state -ne 'Running' -or $Original.state.peers -cne $script:pollOld){
        Set-PollHold 'EXPECTED_RUNNING_0X9_NOT_PRESENT_NO_CHANGE';return
    }
    $refs=@(Measure-Refs 'poll-before')
    if(-not (Check-Offsets $refs)){Set-PollHold 'EXTERNAL_REFERENCE_NOT_IN_SAFE_RANGE_NO_CHANGE';return}
    $before=Query-Time 'poll-before'
    $beforeQpc=Poll-Now
    if(-not (Has-PollFields $before)){Set-PollHold 'BASELINE_SYNC_FIELDS_UNAVAILABLE_NO_CHANGE';return}
    if(Check-Sync $before $Original.state){Set-PollHold 'ALREADY_SYNCHRONIZED_NO_CHANGE';return}
    $latest=Get-PollSnapshot 'poll-preapply'
    if(-not (Same-PollSnapshot $Original $latest $script:pollOld)){Set-PollHold 'CONFIG_DRIFT_BEFORE_APPLY_NO_CHANGE';return}
    try{Check-Preflight $latest.state (Get-Management)}
    catch{Set-PollHold $_.Exception.Message;return}
    # Save restoration instructions before the first mutating command.
    Write-PollRollback
    $changeQpc=Poll-Now
    $script:status.change_qpc_s=$changeQpc
    $script:changed=$true
    $script:status.clock_correction_attempted=$true
    $script:status.mutation_attempted=$true
    Note 'APPLY_POLL_FLAG_0X9_TO_0X8'
    Require-Ok (Set-PollPeer $script:pollNew 'apply-peer') 'APPLY_COMMAND_FAILED'
    $applied=Get-PollSnapshot 'poll-applied'
    if(-not (Same-PollSnapshot $Original $applied $script:pollNew)){Set-PollHold 'CONFIG_CHANGE_NOT_ISOLATED';return}
    Note 'SINGLE_RESYNC_REQUEST'
    $res=Native 'w32tm.exe' @('/resync','/rediscover') 60 'poll-resync'
    $script:status.resync_exit=$res.exit
    # Exit zero or a localized success message is not a sync certificate.
    $fresh=$false
    for($i=1;$i -le 6;$i++){
        $q=Query-Time ("poll-settle-"+$i)
        $now=Poll-Now
        $ok=(Check-Sync $q $applied.state)
        $fresh=(Test-FreshPoll $before $q $beforeQpc $changeQpc $now)
        Save-Json ("poll-settle-"+$i+"-decision.json") @{qpc_s=$now;sync_ok=$ok;fresh=$fresh}
        Note ("SYNC_OBSERVATION=$i healthy=$ok fresh=$fresh")
        if($ok -and $fresh){break}
        if($i -lt 6){Poll-Wait 10}
    }
    if(-not ($ok -and $fresh)){Set-PollHold 'NO_FRESH_SERVICE_SYNC_AFTER_SINGLE_RESYNC';return}
    $results=@()
    foreach($phase in @('poll-after-1','poll-after-2')){
        if($phase -eq 'poll-after-2'){Note 'VERIFY_WINDOW_2_AFTER_30S';Poll-Wait 30}
        $rows=@(Measure-Refs $phase)
        $q=Query-Time $phase
        $now=Poll-Now
        $snap=Get-PollSnapshot $phase
        $row=@{phase=$phase;qpc_s=$now;offsets_pass=(Check-Offsets $rows);sync_pass=(Check-Sync $q $applied.state);fresh=(Test-FreshPoll $before $q $beforeQpc $changeQpc $now);config_isolated=(Same-PollSnapshot $Original $snap $script:pollNew)}
        $results+=$row
        Note ("POLL_WINDOW="+$phase+" offsets="+$row.offsets_pass+" sync="+$row.sync_pass+" fresh="+$row.fresh+" isolated="+$row.config_isolated)
    }
    Save-Json 'poll-verify-summary.json' $results
    if(@($results|Where-Object {-not $_.offsets_pass -or -not $_.sync_pass -or -not $_.fresh -or -not $_.config_isolated}).Count){Set-PollHold 'POST_CHANGE_GATE_FAILED';return}
    $script:status.result='WINDOWS_POLL_CHANGE_CANDIDATE_REVIEW_REQUIRED'
}
function Complete-Poll($Original) {
    $candidate=($script:status.result -eq 'WINDOWS_POLL_CHANGE_CANDIDATE_REVIEW_REQUIRED' -and $script:changed -and -not $script:status.error)
    if($candidate){
        try{
            $final=Get-PollSnapshot 'poll-final'
            if(-not (Same-PollSnapshot $Original $final $script:pollNew)){Set-PollHold 'FINAL_CONFIG_DRIFT';$candidate=$false}
        }catch{$script:status.error=$_.Exception.Message;$candidate=$false}
    }
    if(-not $candidate -and $script:changed){Restore-Poll $Original}
    $hold=($script:status.result -eq 'WINDOWS_POLL_CHANGE_HOLD' -and -not $script:status.error -and ((-not $script:changed -and $script:status.rollback -eq 'NOT_NEEDED') -or ($script:changed -and $script:status.rollback -eq 'VERIFIED')))
    $complete=($candidate -or $hold)
    $script:status.execution_status=if($complete){'COMPLETE'}else{'INCOMPLETE'}
    $script:status.acceptance_status=if($candidate){'CANDIDATE_REVIEW_REQUIRED'}else{'HOLD'}
    $script:status.owner_environment_acceptance=$false
    $script:status.flag_retained=$candidate
    if(-not $complete){$script:status.result='WINDOWS_POLL_CHANGE_INCOMPLETE'}
    try{Pack}
    catch{
        # Do not leave a permanent change accepted without evidence.
        $script:status.archive_error=$_.Exception.Message
        if($candidate){Restore-Poll $Original}
        $script:status.result='WINDOWS_POLL_CHANGE_INCOMPLETE'
        $script:status.execution_status='INCOMPLETE'
        $script:status.acceptance_status='HOLD'
        $script:status.flag_retained=$false
        try{Save-Json 'status.json' $script:status}catch{}
        throw 'POLL_EVIDENCE_PACK_FAILED; review local directory and rollback state'
    }
    Write-Host "EXECUTION_STATUS=$($script:status.execution_status)"
    Write-Host "ACCEPTANCE_STATUS=$($script:status.acceptance_status)"
    Write-Host $script:status.result
    Write-Host "ROLLBACK=$($script:status.rollback)"
    Write-Host 'NEXT_ACTION=UPLOAD_EVIDENCE_FOR_REVIEW; NO_AUTOMATIC_RETRY; WSL2_GATE_HOLD'
    if(-not $complete){throw 'WINDOWS_POLL_EXECUTION_INCOMPLETE; review evidence and rollback'}
}
function Invoke-PollLifecycle {
    $original=$null
    $script:status.mode='POLL_CHANGE_0X9_TO_0X8'
    $script:status.mutation_attempted=$false
    try{
        $state=Get-State
        Write-Backup $state
        Write-PollRollback
        Note "BACKUP_SAVED=$script:root"
        $mg=Get-Management
        Save-Json 'poll-management.json' $mg
        try{Save-Json 'poll-time-events-before.json' @(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-Time-Service'} -MaxEvents 50|Select-Object RecordId,TimeCreated,Id,Message)}
        catch{Save-Json 'poll-time-events-before-error.json' @{error=$_.Exception.Message}}
        $original=Get-PollSnapshot 'poll-original'
        if(-not (Same-Config $state $original.state) -or $state.state -ne $original.state.state){Set-PollHold 'BACKUP_STATE_CHANGED_NO_CHANGE'}
        else{Invoke-PollExperiment $original $mg}
    }catch{
        $script:status.error=$_.Exception.Message
        Note ('POLL_EXECUTION_ERROR '+$_.Exception.Message)
    }finally{
        try{Save-Json 'poll-time-events.json' @(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-Time-Service'} -MaxEvents 50|Select-Object RecordId,TimeCreated,Id,Message)}
        catch{Save-Json 'poll-time-events-error.json' @{error=$_.Exception.Message}}
        Complete-Poll $original
    }
}
if($LibraryOnly){return}
if((([int][bool]$VerifyOnly+[int][bool]$Approved+[int][bool]$PollChangeApproved) -ne 1) -or $SourcePin -notmatch '^[0-9a-f]{40}$' -or $SourceSha256 -notmatch '^[0-9a-f]{64}$' -or (Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $SourceSha256){throw 'APPROVAL_OR_SOURCE_HASH_INVALID'}
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'ELEVATED_POWERSHELL_REQUIRED'}
$mutex=New-Object Threading.Mutex($false,'Global\Ch15WindowsTimeRecovery')
$owned=$false
try{
    $owned=$mutex.WaitOne(0)
    if(-not $owned){throw 'ANOTHER_RECOVERY_RUNNING'}
    $script:root=Join-Path $OutputRoot ([Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $script:root -Force|Out-Null
    $script:status=@{result='WINDOWS_TIME_INCOMPLETE';source_pin=$SourcePin;source_sha256=$SourceSha256;clock_correction_attempted=$false;rollback='NOT_NEEDED';owner_environment_acceptance=$false}
    if($PollChangeApproved){
        Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $script:root 'executed-source.ps1')
        Save-Json 'source-receipt.json' @{pin=$SourcePin;sha256=$SourceSha256;poll_change_approved=$true;approved=$false;verify_only=$false}
        Invoke-PollLifecycle
        return
    }
    $original=$null
    try{
        Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $script:root 'executed-source.ps1')
        Save-Json 'source-receipt.json' @{pin=$SourcePin;sha256=$SourceSha256;approved=[bool]$Approved;verify_only=[bool]$VerifyOnly}
        $original=Get-State
        $script:status.verify_only=[bool]$VerifyOnly
        if($VerifyOnly){
            Save-Json 'before-state.json' $original
            Invoke-VerifyOnly $original
        }else{
            Write-Backup $original
            Note "BACKUP_SAVED=$script:root"
            $mgmt=Get-Management;Save-Json 'management.json' $mgmt
            [void](Native 'wsl.exe' @('--list','--verbose') 20 'wsl-inventory')
            Invoke-Repair $original $mgmt
        }
    }catch{
        $script:status.error=$_.Exception.Message
        Note ('RECOVERY_NOT_ACCEPTED '+$_.Exception.Message)
    }finally{
        if($script:status.result -ne 'WINDOWS_TIME_CANDIDATE_REVIEW_REQUIRED' -and $script:changed){
            try{Restore-State $original;$script:status.rollback='VERIFIED'}
            catch{$script:status.rollback='FAILED_OR_UNVERIFIED';$script:status.rollback_error=$_.Exception.Message}
        }
        try{Save-Json 'final-state.json' (Get-State)}catch{$script:status.final_state_error=$_.Exception.Message}
        try{[void](Native 'sc.exe' @('qtriggerinfo','W32Time') 15 'service-triggers-after')}catch{}
        try{Save-Json 'time-events.json' @(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-Time-Service'} -MaxEvents 30|Select-Object TimeCreated,Id,Message)}
        catch{Save-Json 'time-events-error.json' @{error=$_.Exception.Message}}
        Complete-Run
    }
}finally{
    if($owned){$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
