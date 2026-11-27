#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions ros-jazzy-nav2-msgs ros-jazzy-tf2-ros-py ros-jazzy-lifecycle-msgs ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-action-msgs
source /opt/ros/jazzy/setup.bash
dpkg-query -W > /evidence/dpkg-versions.txt
mkdir -p /tmp/ch15-build; cd /tmp/ch15-build
colcon build --base-paths /ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_safety ch15_mission --event-handlers console_direct+
source install/setup.bash
export G02_INSTALL="$PWD/install" ROS_DOMAIN_ID=72 ROS_LOCALHOST_ONLY=1
timeout --signal=INT --kill-after=20s 80s python3 /ch15/tests/g02_boundaries_probe.py /evidence/boundaries
