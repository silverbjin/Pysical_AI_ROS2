#!/usr/bin/env bash
set -e
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
reuse_out=$1
cat /proc/sys/kernel/random/boot_id > "$reuse_out/boot_id.txt"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/audit_r2_install.py" "$reuse_out/install_audit.json"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/pre_residual.json"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/run_r2_probe.py" --repo-root "$reuse_repo" --evidence "$reuse_out" --launch > "$reuse_out/probe_stdout.log" 2>&1
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/verify_r2_probe.py" "$reuse_out" > "$reuse_out/stop_verifier.log" 2>&1
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/residual_processes.json"
