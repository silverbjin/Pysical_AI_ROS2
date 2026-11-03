#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
reuse_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
reuse_build=${CH13_REUSE_BUILD:-/home/jinho/ch13_reuse_r2_build}
mkdir -p "$reuse_build"
cd "$reuse_build"
colcon --log-base log build --base-paths "$reuse_repo/Ch13/ros2_ws/src/ch13_reuse_wire" "$reuse_repo/Ch13/ros2_ws/src/ch13_navigation_reuse" "$reuse_repo/Ch13/ros2_ws/src/integrated_robot_vision" --build-base build --install-base install --packages-select ch13_reuse_wire ch13_navigation_reuse integrated_robot_vision --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release
