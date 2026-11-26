#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions ros-jazzy-nav2-msgs ros-jazzy-tf2-ros-py ros-jazzy-lifecycle-msgs ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-action-msgs
source /opt/ros/jazzy/setup.bash
dpkg-query -W > /evidence/dpkg-versions.txt
python3 -m unittest discover -s /ch15/tests -p 'test_g02_contract.py' -v
python3 -m unittest discover -s /ch15/tests -p 'test_icd.py' -v
mkdir -p /tmp/ch15-build; cd /tmp/ch15-build
colcon build --base-paths /ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_safety ch15_mission --event-handlers console_direct+
source install/setup.bash
export G02_INSTALL="$PWD/install" ROS_DOMAIN_ID=71 ROS_LOCALHOST_ONLY=1
for iface in action/PickObject action/PlaceObject srv/SwitchGait msg/MissionStatus msg/TargetObservation msg/SafetyState msg/ReadyState msg/MissionEvent; do
  ros2 interface show "ch15_interfaces/$iface" > "/evidence/${iface//\//_}.txt"
done
timeout 15s ros2 launch ch15_mission mission.launch.py --show-args > /evidence/launch-args.txt
timeout --signal=INT --kill-after=20s 100s python3 /ch15/tests/g02_dds_probe.py /evidence/dds
