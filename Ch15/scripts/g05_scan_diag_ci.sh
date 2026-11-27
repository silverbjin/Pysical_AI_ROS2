#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions ros-jazzy-nav2-msgs ros-jazzy-tf2-ros-py ros-jazzy-lifecycle-msgs ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-action-msgs ros-jazzy-rosbag2 ros-jazzy-rosbag2-storage-mcap
source /opt/ros/jazzy/setup.bash
dpkg-query -W >/evidence/dpkg-versions.txt
mkdir /tmp/g05diag; cd /tmp/g05diag
colcon build --base-paths /repo/Ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_safety --event-handlers console_direct+
source install/setup.bash
timeout --signal=INT --kill-after=20s 120s python3 /repo/Ch15/tests/g05_scan_diag.py /evidence/diagnostic
