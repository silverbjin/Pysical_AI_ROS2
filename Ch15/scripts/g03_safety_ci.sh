#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions ros-jazzy-nav2-msgs ros-jazzy-tf2-ros-py ros-jazzy-lifecycle-msgs ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-action-msgs ros-jazzy-py-trees
source /opt/ros/jazzy/setup.bash
dpkg-query -W > /evidence/dpkg-versions.txt
mkdir -p /tmp/ch15-g03; cd /tmp/ch15-g03
colcon build --base-paths /ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_safety ch15_mission --event-handlers console_direct+
source install/setup.bash
export G03_INSTALL="$PWD/install" ROS_LOCALHOST_ONLY=1
# Independent cases: retain all case results even if an earlier boundary fails.
set +e
ROS_DOMAIN_ID=76 timeout --signal=INT --kill-after=20s 60s python3 /ch15/tests/g03_target_probe.py /evidence/target
a=$?
ROS_DOMAIN_ID=77 timeout --signal=INT --kill-after=20s 60s python3 /ch15/tests/g03_fault_probe.py cancel /evidence/cancel
b=$?
ROS_DOMAIN_ID=78 timeout --signal=INT --kill-after=20s 70s python3 /ch15/tests/g03_fault_probe.py invalid_target /evidence/invalid-target
c=$?
set -e
printf 'target=%s cancel=%s invalid_target=%s\n' "$a" "$b" "$c" | tee /evidence/case-exits.txt
if (( a || b || c )); then
  for log in /evidence/target/*.log /evidence/cancel/*.log /evidence/invalid-target/*.log; do echo "===== $log ====="; tail -n 40 "$log"; done
  exit 1
fi
