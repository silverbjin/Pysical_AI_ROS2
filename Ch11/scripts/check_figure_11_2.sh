#!/usr/bin/env bash
# Read-only ROS diagnostics. Source ROS and Ch11 install/setup.bash first.
set -u
if ! command -v ros2 >/dev/null; then
  echo "ROS 2 not available: source /opt/ros/jazzy/setup.bash and Ch11 install/setup.bash."
  exit 2
fi
check() {
  printf '\n'
  printf '%q ' "$@"
  printf '\n'
  timeout 6s "$@"
  printf 'exit=%s (124 = observation timeout)\n' "$?"
}
check ros2 pkg prefix my_quadruped_bot
check ros2 node list
check ros2 topic echo /clock --once
check ros2 topic info /scan -v
check ros2 topic echo /scan --once --field header --qos-reliability best_effort
check ros2 topic echo /imu/data_raw --once --qos-reliability best_effort
check ros2 topic echo /figure_11_2/imu_pose --once
check ros2 run tf2_ros tf2_echo odom base_link
check ros2 run tf2_ros tf2_echo odom lidar_link
echo "Diagnostic collection ended. This script does not certify GUI rendering."
