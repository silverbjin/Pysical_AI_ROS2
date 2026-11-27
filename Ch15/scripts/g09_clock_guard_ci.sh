#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-nav2-msgs ros-jazzy-tf2-ros
source /opt/ros/jazzy/setup.bash
mkdir /tmp/g09guard;cd /tmp/g09guard
colcon build --base-paths /repo/Ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_safety --event-handlers console_direct+ 2>&1 | tee /evidence/build.log
source install/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
unset ROS_STATIC_PEERS ROS_DISCOVERY_SERVER CYCLONEDDS_URI
case "${G09_GUARD_CASE:-both}" in
 both) cases=(forward:97 rewind:98);;
 forward) cases=(forward:97);;
 rewind) cases=(rewind:98);;
 *) exit 2;;
esac
domains=()
for case in "${cases[@]}"; do
 export ROS_DOMAIN_ID="${case#*:}"
 domains+=("$ROS_DOMAIN_ID")
 timeout --signal=INT --kill-after=20s 45s python3 /repo/Ch15/tests/g09_clock_guard_probe.py "/evidence/${case%:*}" "${case%:*}"
done
python3 /repo/Ch15/scripts/owner_graph_audit.py /evidence/residual.json "${domains[@]}"
echo CH15_R03_CLOCK_GUARD_PASS
