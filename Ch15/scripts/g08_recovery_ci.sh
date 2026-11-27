#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions python3-yaml ros-jazzy-rosbag2 ros-jazzy-rosbag2-storage-mcap ros-jazzy-py-trees ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-nav2-msgs ros-jazzy-tf2-ros ros-jazzy-nav2-behaviors
source /opt/ros/jazzy/setup.bash
mkdir /tmp/g08recovery; cd /tmp/g08recovery
colcon build --base-paths /repo/Ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_safety ch15_mission --event-handlers console_direct+ 2>&1 | tee /evidence/build.log
source install/setup.bash
export G03_INSTALL="$PWD/install" ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
unset ROS_STATIC_PEERS ROS_DISCOVERY_SERVER CYCLONEDDS_URI
python3 -m unittest discover -s /repo/Ch15/tests -p test_g08_contracts.py -v 2>&1 | tee /evidence/contracts.log
case "${G08_CASES:-search}" in
 search) cases=(F03_transient:90 F03_persistent:91 F04:92);;
 pick) cases=(F06:93);;
 *) exit 2;;
esac
for case in "${cases[@]}"; do
 export ROS_DOMAIN_ID="${case#*:}"
 mode="${case%:*}"
 timeout --signal=INT --kill-after=20s 100s python3 /repo/Ch15/tests/g08_record_probe.py "$mode" "/evidence/$mode"
 python3 /repo/Ch15/python/g08_analyze.py "/evidence/$mode" "$mode"
done
echo CH15_G08_RECOVERY_SCOPED_PASS
