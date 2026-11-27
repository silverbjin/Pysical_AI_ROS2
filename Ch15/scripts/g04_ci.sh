#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends python3-colcon-common-extensions python3-opencv python3-numpy ros-jazzy-cv-bridge ros-jazzy-tf2-ros-py ros-jazzy-ros-gz-bridge ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-nav2-msgs >/dev/null
source /opt/ros/jazzy/setup.bash
dpkg-query -W >/evidence/dpkg-versions.txt
# RED against exact pre-G04 module absence; never counts a missing dependency as RED.
set +e
python3 -m unittest discover -s /red/Ch15/tests -p 'test_physical_adapter.py' -v >/evidence/red.log 2>&1
rc=$?
set -e
test "$rc" -ne 0
grep -q 'ModuleNotFoundError.*ch15_adapters.ch13_basic_adapter' /evidence/red.log
for t in test_physical_adapter.py test_cube_witness.py; do
  python3 -m unittest discover -s /ch15/tests -p "$t" -v 2>&1 | tee "/evidence/${t%.py}.log"
done
mkdir -p /tmp/ch15-g04; cd /tmp/ch15-g04
colcon build --base-paths /ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_simulation --event-handlers console_direct+
source install/setup.bash
export ROS_DOMAIN_ID=79
bash /ch15/scripts/run_cube_lab.sh /evidence/cube
