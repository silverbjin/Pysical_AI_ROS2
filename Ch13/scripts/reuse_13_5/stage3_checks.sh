#!/usr/bin/env bash
set -e
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
reuse_out=$reuse_repo/Ch13/evidence/section_13_5_reuse/r2_stage3_20261102
bash "$reuse_repo/Ch13/scripts/reuse_13_5/build_r2.sh" > "$reuse_out/build.log" 2>&1
bash "$reuse_repo/Ch13/scripts/reuse_13_5/test_r2.sh" "$reuse_out/tests.log"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/audit_r2_install.py" "$reuse_out/install_audit.json"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/pre_physics_residual.json"
