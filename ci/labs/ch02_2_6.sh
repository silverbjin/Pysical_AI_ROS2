#!/usr/bin/env bash
# Ch02/docs/LAB_2_6_GUIDE_KO.md: ready/build and Action CLI Goal/Result.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
set +u
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID=52
cd "$ROOT/Ch02/ros2_ws"
# Fresh GitHub runner has no rosdep database even after ROS packages are installed.
if test ! -s /etc/ros/rosdep/sources.list.d/20-default.list; then
  sudo rosdep init
fi
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
set +u
source install/setup.bash
set -u
ros2 pkg prefix my_robot_system
ros2 pkg prefix my_robot_interfaces
ros2 interface show my_robot_interfaces/action/CountUntil

ros2 run my_robot_system count_until_server > "$ROOT/ci-results/Ch02/2.6/server.log" 2>&1 &
SERVER_PID=$!
cleanup() {
  kill -INT "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT
READY=0
for _ in $(seq 1 40); do
  if ros2 action list -t 2>/dev/null | grep -q '/count_until'; then
    READY=1
    break
  fi
  sleep 0.5
done
if [ "$READY" -ne 1 ]; then
  echo "CountUntil action server not ready" >&2
  exit 1
fi

timeout 30s ros2 action info /count_until
timeout 30s ros2 action send_goal \
  /count_until my_robot_interfaces/action/CountUntil \
  '{target_number: 5, period: 0.1}' --feedback \
  | tee "$ROOT/ci-results/Ch02/2.6/goal.log"
grep -q 'SUCCEEDED' "$ROOT/ci-results/Ch02/2.6/goal.log"
grep -Eq 'reached_number[=: ]+5' "$ROOT/ci-results/Ch02/2.6/goal.log"
echo "CH02_2_6_GOAL_RESULT_PASS"
# Rejections, client cancellation and GUI remain NOT_RUN, not PASS.
