#!/usr/bin/env bash
# Run after sourcing ROS Jazzy and this chapter's overlay, with mapping active.
set -euo pipefail
chapter="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
map_prefix="${1:-$chapter/maps/my_lab_map}"
if ! command -v ros2 >/dev/null; then
  echo 'Source /opt/ros/jazzy/setup.bash and Ch11/ros2_ws/install/setup.bash first.' >&2
  exit 2
fi
mkdir -p "$(dirname "$map_prefix")"
# Prevent quietly replacing a previous run's map.
for suffix in yaml pgm png; do
  if [ -e "$map_prefix.$suffix" ]; then
    echo "Map already exists: $map_prefix.$suffix; choose a new prefix." >&2
    exit 2
  fi
done
ros2 run nav2_map_server map_saver_cli -t /map -f "$map_prefix" --fmt pgm --free 0.196 --occ 0.65 \
  --ros-args -p use_sim_time:=true -p save_map_timeout:=10.0 \
  -p map_subscribe_transient_local:=true
test -s "$map_prefix.yaml"
test -s "$map_prefix.pgm"
echo "Saved: $map_prefix.yaml and $map_prefix.pgm"
