#!/usr/bin/env bash
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/diagnose_r2_shutdown.py" > "$reuse_repo/Ch13/evidence/section_13_5_reuse/r2_stage1_20261102/shutdown_diagnostic.log" 2>&1
reuse_code=$?
tail -n 35 "$reuse_repo/Ch13/evidence/section_13_5_reuse/r2_stage1_20261102/shutdown_diagnostic.log"
exit "$reuse_code"
