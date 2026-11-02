#!/usr/bin/env bash
set -e
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
reuse_log=${1:-$reuse_repo/Ch13/evidence/section_13_5_reuse/r2_stage1_20261102/tests.log}
set +e
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" -m unittest discover -s "$reuse_repo/Ch13/ros2_ws/src/ch13_navigation_reuse/test" -v > "$reuse_log" 2>&1
reuse_code=$?
tail -n 24 "$reuse_log"
exit "$reuse_code"
