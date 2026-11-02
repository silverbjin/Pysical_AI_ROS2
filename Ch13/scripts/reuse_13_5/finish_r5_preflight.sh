#!/usr/bin/env bash
set -e
reuse_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export CH13_REUSE_BUILD=/home/jinho/ch13_reuse_r5_build
reuse_out=$1
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$reuse_repo/Ch13/ros2_ws/src/integrated_robot_vision:${PYTHONPATH:-}"
/usr/bin/python3 -m pytest -q "$reuse_repo/Ch13/tests/test_section_13_3_policy.py" "$reuse_repo/Ch13/tests/test_section_13_4_geometry.py" "$reuse_repo/Ch13/tests/test_section_13_4_freshness.py" "$reuse_repo/Ch13/tests/test_section_13_4_camera_info.py" > "$reuse_out/legacy_pure_regressions.log" 2>&1
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" -m pip freeze > "$reuse_out/pip_freeze.txt"
dpkg-query -W 'ros-jazzy-nav2-*' > "$reuse_out/nav2_packages.txt"
bash "$reuse_repo/Ch13/scripts/reuse_13_5/env_r2.sh" "$reuse_repo/Ch13/scripts/reuse_13_5/inspect_r2_residuals.py" "$reuse_out/residual_processes.json"
