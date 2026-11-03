#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=135 PYTHONDONTWRITEBYTECODE=1
export CH13_REUSE_BUILD=${CH13_REUSE_BUILD:-/home/jinho/ch13_reuse_13_6_build}
export CH13_REUSE_VENV=${CH13_REUSE_VENV:-/home/jinho/ch13_reuse_iit_d010212_venv}
source "$CH13_REUSE_BUILD/install/setup.bash"
export MUJOCO_GL=egl LP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
exec "$CH13_REUSE_VENV/bin/python" "$@"
