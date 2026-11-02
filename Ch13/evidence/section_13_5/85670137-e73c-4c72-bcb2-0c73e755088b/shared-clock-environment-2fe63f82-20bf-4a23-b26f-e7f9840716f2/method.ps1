$ErrorActionPreference='Stop'
$repoRoot='C:/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2'
$root=Join-Path $repoRoot ('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b/shared-clock-environment-'+[guid]::NewGuid().ToString())
[IO.Directory]::CreateDirectory($root)|Out-Null
[IO.File]::Copy($PSCommandPath,(Join-Path $root 'method.ps1'))
$probe='import json,pathlib,subprocess,os; commands=[["systemctl","show","systemd-timesyncd.service","--property=ActiveState,SubState,ExecMainPID"],["systemctl","is-enabled","systemd-timesyncd.service"],["timedatectl","timesync-status"],["journalctl","-b","-u","systemd-timesyncd.service","--no-pager","-n","18"]]; rows=[]; exec("for c in commands:\n p=subprocess.run(c,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15); rows.append(dict(command=c,returncode=p.returncode,output=p.stdout))"); print(json.dumps(dict(uid=os.getuid(),boot_id=pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip(),clocksource=pathlib.Path("/sys/devices/system/clocksource/clocksource0/current_clocksource").read_text().strip(),clock_ticks=os.sysconf("SC_CLK_TCK"),namespaces={k:os.readlink("/proc/self/ns/"+k) for k in ["pid","time","uts"]},commands=rows)))'
$rows=@()
foreach($distro in @('Ubuntu-22.04','Ubuntu-24.04')) {
    $raw=& wsl -d $distro -u jinho -- python3 -c $probe
    if($LASTEXITCODE -ne 0){throw ('Read-only probe failed '+$distro)}
    $rows+=@{distribution=$distro;report=($raw|ConvertFrom-Json)}
}
$distroOutput=(& wsl --list --verbose)-join "`n"
$data=[ordered]@{scope='read_only_shared_kernel_environment_not_engine_acceptance';utc=[DateTimeOffset]::UtcNow.ToString('o');distributions=$rows;wsl_listing=($distroOutput.Replace([string][char]0,''));host_services=@(Get-Service W32Time,vmictimesync|Select-Object Name,@{Name='Status';Expression={$_.Status.ToString()}},@{Name='StartType';Expression={$_.StartType.ToString()}});writes_system_settings=$false}
[IO.File]::WriteAllText((Join-Path $root 'result.json'),($data|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Write-Output $root
