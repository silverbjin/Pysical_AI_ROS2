#!/usr/bin/env bash
# Incremental rebuild after the initial eight-package build. No engine may be active.
set -eo pipefail
validation_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export CH13_REUSE_BUILD=${CH13_REUSE_BUILD:-/home/jinho/ch13_reuse_13_8_build}
/usr/bin/python3 "$validation_repo/Ch13/ros2_ws/src/ch13_system_validation/ch13_system_validation/tools.py" "$CH13_REUSE_BUILD"
source /opt/ros/jazzy/setup.bash
source "$CH13_REUSE_BUILD/install/setup.bash"
cd "$CH13_REUSE_BUILD"
colcon --log-base log build --base-paths "$validation_repo/Ch13/ros2_ws/src/ch13_navigation_reuse" \
 "$validation_repo/Ch13/ros2_ws/src/ch13_reuse_wire" \
 "$validation_repo/Ch13/ros2_ws/src/ch13_manipulation_reuse" "$validation_repo/Ch13/ros2_ws/src/ch13_mission_orchestration" \
 "$validation_repo/Ch13/ros2_ws/src/ch13_system_validation" --build-base build --install-base install \
 --packages-select ch13_reuse_wire ch13_navigation_reuse ch13_manipulation_reuse ch13_mission_orchestration ch13_system_validation \
 --event-handlers console_direct+
