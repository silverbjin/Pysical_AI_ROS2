$ErrorActionPreference='Stop'
$repoRoot='C:/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2'
$outputRoot=Join-Path $repoRoot ('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b/clock-cross-boundary-'+[guid]::NewGuid().ToString())
[IO.Directory]::CreateDirectory($outputRoot)|Out-Null
[IO.File]::Copy($PSCommandPath,(Join-Path $outputRoot 'method.ps1'))
$frequency=[Diagnostics.Stopwatch]::Frequency
$command='import json,time,pathlib,os; a=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW); r=time.time_ns(); m=time.monotonic_ns(); b=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW); print(json.dumps(dict(raw_before_ns=a,realtime_ns=r,monotonic_ns=m,raw_after_ns=b,uid=os.getuid(),boot_id=pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip())))'
$watch=[Diagnostics.Stopwatch]::StartNew()
$writer=[IO.StreamWriter]::new((Join-Path $outputRoot 'samples.jsonl'),$false,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $outputRoot 'start.json'),([ordered]@{scope='read_only_host_QPC_brackets_original_guest_clocks';qpc_frequency=$frequency;command=$command;duration_seconds=60;writes_system_settings=$false}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
Write-Output $outputRoot
try {
    for($index=0;$index -le 6;$index++) {
        while($watch.Elapsed.TotalSeconds -lt $index*10){Start-Sleep -Milliseconds 50}
        $before=[Diagnostics.Stopwatch]::GetTimestamp()
        $utcBefore=[DateTimeOffset]::UtcNow.ToString('o')
        $guest=& wsl -d Ubuntu-24.04 -u jinho -- python3 -c $command
        $exit=$LASTEXITCODE
        $utcAfter=[DateTimeOffset]::UtcNow.ToString('o')
        $after=[Diagnostics.Stopwatch]::GetTimestamp()
        if($exit -ne 0){throw ('read-only guest clock query failed '+$exit)}
        $row=[ordered]@{qpc_before=$before;qpc_after=$after;utc_before=$utcBefore;utc_after=$utcAfter;guest=($guest|ConvertFrom-Json)}
        $writer.WriteLine(($row|ConvertTo-Json -Depth 4 -Compress));$writer.Flush()
    }
} finally {$writer.Dispose()}
$result=[ordered]@{scope='diagnosis_not_engine_acceptance';completed=$true;samples_sha256=(Get-FileHash (Join-Path $outputRoot 'samples.jsonl') -Algorithm SHA256).Hash;writes_system_settings=$false}
[IO.File]::WriteAllText((Join-Path $outputRoot 'result.json'),($result|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
$result|ConvertTo-Json -Compress
