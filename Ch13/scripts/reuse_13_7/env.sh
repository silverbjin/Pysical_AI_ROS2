#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
export CH13_REUSE_BUILD=${CH13_REUSE_BUILD:-/home/jinho/ch13_reuse_13_7_build}
export CH13_REUSE_VENV=${CH13_REUSE_VENV:-/home/jinho/ch13_reuse_iit_d010212_venv}
bt_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
/usr/bin/python3 "$bt_repo/Ch13/ros2_ws/src/ch13_mission_orchestration/ch13_mission_orchestration/tools.py" "$CH13_REUSE_BUILD" >/dev/null
bt_deps="$CH13_REUSE_BUILD/bt_deps/root/opt/ros/jazzy"
if [[ -d "$bt_deps" ]]; then
 export AMENT_PREFIX_PATH="$bt_deps:$AMENT_PREFIX_PATH"
 export PYTHONPATH="$bt_deps/lib/python3.12/site-packages:$PYTHONPATH"
 export LD_LIBRARY_PATH="$bt_deps/lib:$LD_LIBRARY_PATH"
fi
source "$CH13_REUSE_BUILD/install/setup.bash"
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=135 PYTHONDONTWRITEBYTECODE=1
export MUJOCO_GL=egl LP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
exec "$CH13_REUSE_VENV/bin/python" "$@"
