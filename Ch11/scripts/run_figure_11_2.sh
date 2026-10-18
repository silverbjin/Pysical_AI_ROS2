#!/usr/bin/env bash
# Build only Ch11 and launch Gazebo + the book's RViz sensor composition.
set -eo pipefail
chapter="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -n "${VIRTUAL_ENV:-}" ] || [ -n "${CONDA_PREFIX:-}" ]; then
  echo "Deactivate rl_env/venv/Conda and run from a new WSL terminal."
  exit 2
fi
if [ ! -f /opt/ros/jazzy/setup.bash ]; then
  echo "ROS 2 Jazzy is required. See Ch11/docs/FIGURE_11_2_GUIDE_KO.md."
  exit 2
fi
source /opt/ros/jazzy/setup.bash
for program in colcon ros2 gz; do
  if ! command -v "$program" >/dev/null; then
    echo "Missing command: $program"
    exit 2
  fi
done
# ROS_DOMAIN_ID does not isolate Gazebo Transport. Keep clocks, model topics
# and spawn services separate from other chapters running on this host.
export GZ_PARTITION="${GZ_PARTITION:-ch11_figure_11_2_${UID}_$$}"
printf 'ROS_DOMAIN_ID=%s\nGZ_PARTITION=%s\n' "${ROS_DOMAIN_ID:-0}" "$GZ_PARTITION"
cd "$chapter/ros2_ws"
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
prefix="$(ros2 pkg prefix my_quadruped_bot)"
case "$prefix" in
  "$chapter/ros2_ws/install"/*) ;;
  *) echo "Wrong chapter overlay: $prefix"; exit 2 ;;
esac
# Catch model/controller mismatches before starting physics after a merge.
python3 -m unittest discover -s "$chapter/tests" -p test_figure_11_2.py
exec ros2 launch my_quadruped_bot figure_11_2.launch.py "$@"
