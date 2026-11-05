#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
bt_scripts="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bt_repo="$(cd "$bt_scripts/../../.." && pwd)"
bt_build=${CH13_REUSE_BUILD:-/home/jinho/ch13_reuse_13_7_build}
/usr/bin/python3 "$bt_repo/Ch13/ros2_ws/src/ch13_mission_orchestration/ch13_mission_orchestration/tools.py" "$bt_build"
bt_deps="$bt_build/bt_deps/root/opt/ros/jazzy"
if [[ -d "$bt_deps" ]]; then
  export AMENT_PREFIX_PATH="$bt_deps:$AMENT_PREFIX_PATH"
  export PYTHONPATH="$bt_deps/lib/python3.12/site-packages:$bt_build/bt_deps/root/usr/lib/python3/dist-packages:$PYTHONPATH"
  export LD_LIBRARY_PATH="$bt_deps/lib:$LD_LIBRARY_PATH"
fi
/usr/bin/python3 -c 'import py_trees,py_trees_ros'
export CH13_REUSE_BUILD="$bt_build"
# Reuse the model generation and six-package build; this path passed the stricter 13.7 guard.
bash "$bt_repo/Ch13/scripts/reuse_13_6/build.sh"
cd "$bt_build"
source "$bt_build/install/setup.bash"
colcon --log-base log build --base-paths "$bt_repo/Ch13/ros2_ws/src/ch13_mission_orchestration" \
 --build-base build --install-base install --packages-select ch13_mission_orchestration --event-handlers console_direct+
