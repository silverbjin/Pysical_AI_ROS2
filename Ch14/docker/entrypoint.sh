#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source /opt/robot_ws/install/setup.bash
exec "$@"
