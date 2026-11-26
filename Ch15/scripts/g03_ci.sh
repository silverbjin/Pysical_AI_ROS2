#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions ros-jazzy-nav2-msgs ros-jazzy-tf2-ros-py ros-jazzy-lifecycle-msgs ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-action-msgs ros-jazzy-py-trees
source /opt/ros/jazzy/setup.bash
dpkg-query -W > /evidence/dpkg-versions.txt
python3 -c 'import importlib.metadata as m; print(m.version("py_trees"))' | tee /evidence/py-trees-version.txt
# RED test suite against the pre-G03 source, then GREEN against current source.
set +e
python3 -m unittest discover -s /red/Ch15/tests -p 'test_action_supervisor.py' -v > /evidence/red.log 2>&1
red=$?
set -e
test "$red" -ne 0
grep -q 'ModuleNotFoundError.*ch15_mission.action_supervisor' /evidence/red.log
for t in test_action_supervisor.py test_target_contract.py test_mission_tree.py; do
  python3 -m unittest discover -s /ch15/tests -p "$t" -v 2>&1 | tee "/evidence/${t%.py}.log"
done
mkdir -p /tmp/ch15-g03; cd /tmp/ch15-g03
colcon build --base-paths /ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_safety ch15_mission --event-handlers console_direct+
source install/setup.bash
export G03_INSTALL="$PWD/install" ROS_LOCALHOST_ONLY=1
timeout 15s ros2 launch ch15_mission mission.launch.py --show-args > /evidence/launch-args.txt
ROS_DOMAIN_ID=74 timeout --signal=INT --kill-after=20s 90s python3 /ch15/tests/g03_action_probe.py /evidence/action
ROS_DOMAIN_ID=75 timeout --signal=INT --kill-after=20s 100s python3 /ch15/tests/g03_mission_probe.py /evidence/mission
