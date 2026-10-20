#!/usr/bin/env bash
# 2.2절 ROS CLI 연결 점검: 실제 turtlesim이 실행 중일 때만 실행한다.
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "사용법: bash Ch02/scripts/check_turtlesim_cli.sh (turtlesim 실행 후)"
  exit 0
fi
if [[ $# -gt 0 ]]; then
  echo "오류: 지원하지 않는 인자입니다. --help를 사용하세요." >&2
  exit 2
fi
if ! command -v ros2 >/dev/null 2>&1; then
  echo "BLOCKED: ROS 2 CLI가 PATH에 없습니다 (source /opt/ros/jazzy/setup.bash)." >&2
  exit 2
fi
if ! ros2 node list | grep -Fxq /turtlesim; then
  echo "BLOCKED: /turtlesim 노드가 없습니다. ros2 run turtlesim turtlesim_node 실행 필요." >&2
  exit 3
fi

echo "[1/4] ROS nodes"
ros2 node list
echo "[2/4] Topic type and endpoints"
ros2 topic list -t
cmd_type="$(ros2 topic type /turtle1/cmd_vel)"
[[ "$cmd_type" == "geometry_msgs/msg/Twist" ]] || {
  echo "FAIL: Unexpected cmd_vel type: $cmd_type" >&2; exit 4;
}
ros2 topic info --verbose /turtle1/cmd_vel
echo "[3/4] Pose type"
pose_type="$(ros2 topic type /turtle1/pose)"
[[ "$pose_type" == "turtlesim/msg/Pose" ]] || {
  echo "FAIL: Unexpected pose type: $pose_type" >&2; exit 5;
}
echo "[4/4] Spawn service contract"
service_type="$(ros2 service type /spawn)"
[[ "$service_type" == "turtlesim/srv/Spawn" ]] || {
  echo "FAIL: Unexpected /spawn type: $service_type" >&2; exit 6;
}
echo "CONTRACT_PASS: turtlesim node, topic and service types"
