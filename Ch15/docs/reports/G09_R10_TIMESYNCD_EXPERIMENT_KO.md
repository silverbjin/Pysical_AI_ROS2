# G09-R10 — 승인된 단일 변수 실험 (candidate)
승인 범위: Ubuntu systemd-timesyncd.service 일시 stop → 동일 180s RAW trace → start 복원. Windows, chronyd, Hyper-V, tick, enablement, robot safety unchanged. Prior trace 5/5 step/caller correlation, namespace unknown. No mission.
Preflight active/running, MainPID, unit file state, tracefs/tracepoint, sudo, pinned trace hash. Before stop arm and verify independent transient systemd restore timer (360s guest monotonic); failure stops experiment before mutation. Stop verified inactive/dead/PID0; every 5s service poll; 225s RAW upper bound. Normal/error/signal restore with state verification before cancelling timer; timer remains if restoration unverified. Timer only protects while distro/systemd running; abrupt WSL shutdown/power loss or timer/systemd failure not guaranteed. Manual recovery: sudo systemctl start systemd-timesyncd.service. No persistent disable/mask. Trace process group cleanup; forced kill may leave tracefs instance, review. Archive private logs, manifests and source receipts; no environment acceptance. CI mock only, actual user test pending. Baseline previous 180s evidence reused; no repeat baseline. 

Additional review: guard timer active verified again before stop and during each monitored sample; per-user advisory lock to prevent concurrent launcher executions. This does not prevent unrelated administrators/other distros from changing service. CI shallow clone fetches comparison base explicitly. Actual WSL2 still pending.

## Actual CI and owner handoff
- RED run 46025023333 job 140594074560: 8/8 mock tests and pinned trace SHA pass; scope comparison failed fatal bad object because shallow checkout lacked base 8071cae5. Existing clock regression run 46025023101 succeeded. Fix explicitly fetch immutable base and add timer-liveness and service-restart rejection tests.
- GREEN run 46025247533 job 140594855542 SUCCESS: 10/10 mock/integrity tests, Python syntax, immutable trace download hash, Bash syntax, scope check. Owner launcher SHA256 independently computed from fetched blob and matches CI log: 4ad89f807b889a7d2aabec645726bdf3c17d3c4435a0e17a04df4473267c689d. Source PIN b20f9bc7af6066f14a02ccc2e3d3a3486b2a7d99. No actual stop/start or tracefs mutation in CI. User WSL2 NOT_RUN. No final stability acceptance. Existing F06 FAIL, F01 NOT_RUN, main HOLD.
- Owner command (normal Ubuntu WSL user, no active robot mission, no shutdown):
```bash
PIN=b20f9bc7af6066f14a02ccc2e3d3a3486b2a7d99
SHA256=4ad89f807b889a7d2aabec645726bdf3c17d3c4435a0e17a04df4473267c689d
BOOT="$HOME/ch15-clock-timesyncd-experiment.py"
curl -fsSLo "$BOOT" "https://raw.githubusercontent.com/silverbjin/Pysical_AI_ROS2/$PIN/Ch15/scripts/clock_diag_timesyncd_experiment.py" && printf '%s  %s\n' "$SHA256" "$BOOT" | sha256sum -c - && python3 "$BOOT" --source-pin "$PIN" --source-sha256 "$SHA256" --approved
```
- Submit outer tar.gz and tar.gz.sha256 privately even on failure. Source receipt inside. Verify restored active/running + unit-file-state match; if unverified, run sudo systemctl start systemd-timesyncd.service and systemctl is-active systemd-timesyncd.service. Timer is guest monotonic, not guaranteed against VM/systemd loss. No retry until review.
