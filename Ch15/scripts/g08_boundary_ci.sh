#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-nav2-msgs ros-jazzy-tf2-ros
source /opt/ros/jazzy/setup.bash
mkdir /tmp/g08; cd /tmp/g08
colcon build --base-paths /repo/Ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_safety --event-handlers console_direct+ 2>&1 | tee /evidence/build.log
source install/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
unset ROS_STATIC_PEERS ROS_DISCOVERY_SERVER CYCLONEDDS_URI
python3 -m unittest discover -s /repo/Ch15/tests -p test_g08_contracts.py -v 2>&1 | tee /evidence/contracts.log
for case in F01_receipt:86 F01_source:87 F07:88; do
  export ROS_DOMAIN_ID="${case#*:}"
  timeout --signal=INT --kill-after=10s 25s python3 /repo/Ch15/tests/g08_safety_probe.py "/evidence/${case%:*}.json" "${case%:*}"
done
echo CH15_G08_BOUNDARY_PASS
