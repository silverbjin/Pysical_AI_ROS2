#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions ros-jazzy-nav2-msgs ros-jazzy-tf2-ros-py ros-jazzy-lifecycle-msgs ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-action-msgs ros-jazzy-py-trees
source /opt/ros/jazzy/setup.bash
dpkg-query -W > /evidence/dpkg-versions.txt
python3 -c 'import importlib.metadata as m; print(m.version("py_trees"))' | tee /evidence/py-trees-version.txt
mkdir -p /tmp/ch15-g03; cd /tmp/ch15-g03
colcon build --base-paths /ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_safety ch15_mission --event-handlers console_direct+
source install/setup.bash
export G03_INSTALL="$PWD/install" ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=75
set +e
timeout --signal=INT --kill-after=20s 100s python3 /ch15/tests/g03_mission_probe.py /evidence/mission
rc=$?
set -e
if (( rc != 0 )); then
  for log in /evidence/mission/*.log; do echo "===== $log ====="; tail -n 60 "$log"; done
fi
exit "$rc"
