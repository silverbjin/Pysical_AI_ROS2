#!/usr/bin/env bash
set -e
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
export MUJOCO_GL=egl
bash "$reuse_repo/Ch13/scripts/reuse_13_5/test_r4_geometry.sh" "$reuse_repo/Ch13/evidence/section_13_5_reuse/r4_preflight/camera_worker_green.log"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/build_r2.sh" > "$reuse_repo/Ch13/evidence/section_13_5_reuse/r4_preflight/build_worker.log" 2>&1
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/probe_camera_worker.py"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/test_r2.sh" "$reuse_repo/Ch13/evidence/section_13_5_reuse/r4_preflight/tests_worker_78.log"
