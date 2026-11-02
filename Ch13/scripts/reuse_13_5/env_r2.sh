#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=135 PYTHONDONTWRITEBYTECODE=1
reuse_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export CH13_REUSE_BUILD=${CH13_REUSE_BUILD:-/home/jinho/ch13_reuse_r2_build}
export CH13_REUSE_VENV=${CH13_REUSE_VENV:-/home/jinho/ch13_reuse_iit_d010212_venv}
if [[ -f "$CH13_REUSE_BUILD/install/setup.bash" ]]; then
  source "$CH13_REUSE_BUILD/install/setup.bash"
fi
if [[ ! -f $CH13_REUSE_BUILD/install/ch13_navigation_reuse/share/ch13_navigation_reuse/package.xml ]]; then
  export PYTHONPATH="$reuse_repo/Ch13/ros2_ws/src/ch13_navigation_reuse:${PYTHONPATH:-}"
fi
exec "$CH13_REUSE_VENV/bin/python" "$@"
