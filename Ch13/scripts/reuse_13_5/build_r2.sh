#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
reuse_repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse
mkdir -p /home/jinho/ch13_reuse_r2_build
cd /home/jinho/ch13_reuse_r2_build
colcon --log-base log build --base-paths "$reuse_repo/Ch13/ros2_ws/src/ch13_reuse_wire" "$reuse_repo/Ch13/ros2_ws/src/ch13_navigation_reuse" --build-base build --install-base install --packages-select ch13_reuse_wire ch13_navigation_reuse --event-handlers console_direct+
