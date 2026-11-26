#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=verify_reuse
trap 'rc=$?; printf "{\"stage\":\"%s\",\"exit_code\":%d}\n" "$stage" "$rc" > "$out/stage.json"' EXIT
python3 /ch14/scripts/g07_verify_reuse.py --root /reuse | tee "$out/reuse.json"
test -s /ch14/requirements/rl.lock.txt
stage=locked_environment
source /ch14/scripts/g07_env.sh "$out"
apt-get install -y --no-install-recommends ros-jazzy-std-srvs ros-jazzy-visualization-msgs ros-jazzy-rosgraph-msgs >/dev/null
export ROS_DOMAIN_ID=98 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
stage=colcon
mkdir -p /tmp/g08_ws/src
cp -a /ch14/ros2_ws/src/ch14_rl_deployment /tmp/g08_ws/src/
(cd /tmp/g08_ws && python "$(command -v colcon)" build --packages-select ch14_rl_deployment) 2>&1 | tee "$out/colcon.log"
set +u
source /tmp/g08_ws/install/setup.bash
set -u
stage=mujoco_actual
python /ch14/scripts/g08_mujoco_probe.py
stage=complete
