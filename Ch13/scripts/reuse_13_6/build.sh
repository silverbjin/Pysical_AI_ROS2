#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
reuse_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
reuse_build=${CH13_REUSE_BUILD:-/home/jinho/ch13_reuse_13_6_build}
case "$(realpath -m "$reuse_build")" in
  /home/jinho/ch13_reuse_r2_build|/home/jinho/ch13_reuse_r5_build) echo '13.6 requires a separate build directory' >&2; exit 2;;
esac
mkdir -p "$reuse_build"
export CH13_REUSE_GENERATED="$reuse_build/model"
"${CH13_REUSE_VENV:-/home/jinho/ch13_reuse_iit_d010212_venv}/bin/python" "$reuse_repo/Ch13/scripts/reuse_13_6/prepare_model.py" "$CH13_REUSE_GENERATED"
cd "$reuse_build"
colcon --log-base log build --base-paths \
  "$reuse_repo/Ch13/ros2_ws/src/ch13_reuse_wire" \
  "$reuse_repo/Ch13/ros2_ws/src/ch13_navigation_reuse" \
  "$reuse_repo/Ch13/ros2_ws/src/integrated_robot_vision" \
  "$reuse_repo/Ch13/ros2_ws/src/ch13_manipulation_reuse" \
  "$reuse_repo/Ch13/ros2_ws/src/ch13_piper_moveit_config" \
  "$reuse_repo/Ch13/ros2_ws/src/ch13_manipulation_planner" \
  --build-base build --install-base install \
  --packages-select ch13_reuse_wire ch13_navigation_reuse integrated_robot_vision ch13_manipulation_reuse ch13_manipulation_planner ch13_piper_moveit_config \
  --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release
