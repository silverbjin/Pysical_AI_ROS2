#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
bt_root=/home/jinho/ch13_reuse_13_7_build/bt_deps/root/opt/ros/jazzy
export PYTHONPATH="$bt_root/lib/python3.12/site-packages:$(cd "$(dirname "$0")/../../ros2_ws/src/ch13_mission_orchestration" && pwd):$PYTHONPATH"
export LD_LIBRARY_PATH="$bt_root/lib:$LD_LIBRARY_PATH"
export AMENT_PREFIX_PATH="$bt_root:$AMENT_PREFIX_PATH"
export PYTHONDONTWRITEBYTECODE=1
exec /usr/bin/python3 "$@"
