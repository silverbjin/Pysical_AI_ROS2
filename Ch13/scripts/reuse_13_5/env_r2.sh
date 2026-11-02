#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=135 PYTHONDONTWRITEBYTECODE=1
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
if [[ -f /home/jinho/ch13_reuse_r2_build/install/setup.bash ]]; then
  source /home/jinho/ch13_reuse_r2_build/install/setup.bash
fi
if [[ ! -f /home/jinho/ch13_reuse_r2_build/install/ch13_navigation_reuse/share/ch13_navigation_reuse/package.xml ]]; then
  export PYTHONPATH="$reuse_repo/Ch13/ros2_ws/src/ch13_navigation_reuse:${PYTHONPATH:-}"
fi
exec /home/jinho/ch13_reuse_iit_d010212_venv/bin/python "$@"
