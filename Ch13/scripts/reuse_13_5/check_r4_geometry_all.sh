#!/usr/bin/env bash
set +e
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
export MUJOCO_GL=egl
bash "$reuse_repo/Ch13/scripts/reuse_13_5/test_r4_geometry.sh" "$reuse_repo/Ch13/evidence/section_13_5_reuse/r4_preflight/actual_suite_camera_green.log"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" -m unittest discover -s "$reuse_repo/Ch13/ros2_ws/src/ch13_navigation_reuse/test" -p test_approach_geometry.py -v > "$reuse_repo/Ch13/evidence/section_13_5_reuse/r4_preflight/ik_red.log" 2>&1
reuse_code=$?
tail -n 15 "$reuse_repo/Ch13/evidence/section_13_5_reuse/r4_preflight/ik_red.log"
exit "$reuse_code"
