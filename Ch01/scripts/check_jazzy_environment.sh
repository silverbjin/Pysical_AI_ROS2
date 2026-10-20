#!/usr/bin/env bash
# Ch01 §1.2: read-only environment diagnosis; never installs packages.
set -euo pipefail

if [[ ! -r /etc/os-release ]]; then
  echo 'BLOCKED: /etc/os-release not found' >&2; exit 2
fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != ubuntu || "${VERSION_ID:-}" != '24.04' ]]; then
  echo "BLOCKED: Ubuntu 24.04 required (actual: ${ID:-?} ${VERSION_ID:-?})" >&2
  exit 2
fi
if [[ ! -r /opt/ros/jazzy/setup.bash ]]; then
  echo 'BLOCKED: /opt/ros/jazzy/setup.bash missing' >&2; exit 2
fi
if [[ -n "${CONDA_PREFIX:-}" ]]; then
  echo "BLOCKED: active Conda environment: $CONDA_PREFIX" >&2; exit 2
fi
# Run in an isolated process: does not modify the caller's shell.
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
if [[ "${ROS_DISTRO:-}" != jazzy ]]; then
  echo "BLOCKED: expected jazzy, actual ${ROS_DISTRO:-unset}" >&2; exit 2
fi
for executable in ros2 colcon python3; do
  if ! command -v "$executable" >/dev/null 2>&1; then
    echo "BLOCKED: executable not found: $executable" >&2; exit 2
  fi
done
python3 - <<'PY'
import sys
if sys.version_info[:2] != (3, 12):
    raise SystemExit(f'BLOCKED: Python 3.12 required, got {sys.version}')
import rclpy
print('rclpy:', rclpy.__file__)
PY
printf 'PASS: Ubuntu 24.04 / ROS 2 Jazzy / Python 3.12 / rclpy / colcon\n'
printf 'AMENT_PREFIX_PATH=%s\n' "${AMENT_PREFIX_PATH:-unset}"
