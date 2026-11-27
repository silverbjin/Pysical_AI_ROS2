# G05 scan diagnostic — source vs receiver and publication boundary
Actual run 45948457875 job140338492039 artifact15176320683, source a257f990ad9df78601565a6da17c450a7310171f, ZIP90,284 bytes SHA256 a2ef84f214731ae6c39e612c6d1530a7cda5be90840187cfb62961737194db75; 28/28 manifest verified. No motion; 8/8 child exits0.
| case | source max ms | publish max ms | watchdog receive ms | watchdog tick max ms | timing |
|---|---:|---:|---:|---:|---|
| original OFF |100.498|.330|100.538|50.297|PASS|
| original ON |100.410|.316|100.523|50.335|PASS|
| isolated ON |100.214|.318|412.000|361.196|FAIL|
C: publisher/probe continued at 100ms; Watchdog last scan 131818563991, tick observation 131867893491 age .049243, next trace132229089597 age .099283, CPU increment .568ms. Thus about311ms elapsed inside original tick between age sample and return (or descheduling there), not source pause. Next tick latch age .410811. No cgroup CPU throttling, cpu.max max, all source GC intervals <.864ms in these tests. Prior RED4 source pause not reproduced; don't claim sole root cause. Original full producer passes recording-only diagnostic; do not split scan publisher in integrated candidate.
V5: explicit rmw_fastrtps_cpp ASYNCHRONOUS in G05 mock scripts only; original safety limits, source and native QoS unchanged. RMW official docs https://github.com/ros2/rmw_fastrtps explain synchronous publish can block caller; hypothesis async may remove publisher-side stalls, not proof. Timed watchdog pub and callback + mock sample trace. Gate actual no-motion original-on async before normal. If pass, run normal/F01/F06 once and actual typed analysis/replay. Reuse T12 Git/LFS and C15 synthetic smoke. No main merge/physical rerun.
