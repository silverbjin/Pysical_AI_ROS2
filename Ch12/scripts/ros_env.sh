#!/usr/bin/env bash
# Source this after activating the Python environment containing Ch12[train].
chapter="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/jazzy/setup.bash
python_site="$(python -c 'import site; print(site.getsitepackages()[0])')"
export PYTHONPATH="$chapter/src:$python_site:${PYTHONPATH:-}:/usr/lib/python3/dist-packages"
if [ -f "$chapter/../Ch11/ros2_ws/install/setup.bash" ]; then
  source "$chapter/../Ch11/ros2_ws/install/setup.bash"
fi
if [ -f "$chapter/ros2_ws/install/setup.bash" ]; then
  source "$chapter/ros2_ws/install/setup.bash"
fi
