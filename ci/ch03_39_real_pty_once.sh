#!/usr/bin/env bash
# Ch03 §3.9: original interactive teleop, actual Linux PTY and ROS Float64.
# NO Gazebo, no robot, Ch10 HOLD. No replay of accepted Ch03 world/clock.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work;OUT="$ROOT/ci-results/ch03-39";mkdir -p "$OUT"
export ROS_DOMAIN_ID=39 ROS_LOCALHOST_ONLY=1 PYTHONUNBUFFERED=1
printf 'source_sha=%s\n' "${RUN_SOURCE_SHA:-UNKNOWN}" > "$OUT/environment.txt"
cd "$ROOT/Ch03/ros2_ws"
echo "STAGE=REAL_PACKAGE_BUILD" | tee -a "$OUT/stages.log"
timeout --signal=TERM --kill-after=6s 120s \
 colcon build --symlink-install --packages-select my_robot_description \
 > "$OUT/colcon.log" 2>&1
set +u;source install/setup.bash;set -u
ros2 pkg executables my_robot_description > "$OUT/executables.txt"
grep -q 'my_robot_description simple_arm_teleop' "$OUT/executables.txt"
echo "STAGE=ACTUAL_LINUX_TTY_WITH_ROS_INPUT_TOPICS" | tee -a "$OUT/stages.log"
export CH03_39_OUT="$OUT"
timeout --signal=TERM --kill-after=8s 65s \
 python3 "$ROOT/ci/ch03_39_real_pty_once.py" \
 2>&1 | tee "$OUT/tty_probe.log"
grep -q CH03_39_REAL_INTERACTIVE_TTY_AND_ROS_COMMAND_SCOPED_PASS "$OUT/tty_probe.log"
python3 - "$OUT/result.json" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r["status"]=="SCOPED_PASS" and r["chapter"]=="Ch03" and r["section"]=="3.9"
assert r["observed_transitions"]==[
  {"key":"w","joint1_rad":0.05,"joint2_rad":0.0},
  {"key":"w","joint1_rad":0.10,"joint2_rad":0.0},
  {"key":"a","joint1_rad":0.10,"joint2_rad":0.05},
  {"key":"d","joint1_rad":0.10,"joint2_rad":0.0},
  {"key":"s","joint1_rad":0.05,"joint2_rad":0.0},
]
assert r["child_exit_code"]==0
assert r["tty_attributes_restored"] and r["idle_no_republish"] and r["ros_node_gone"]
assert r["gazebo_joint_feedback"]=="NOT_RUN" and r["ch10"]=="HOLD"
print("CH03_39_INDEPENDENT_PTY_ROS_RECEIPT_PASS")
PY
echo "STAGE=CH03_39_REAL_TTY_SCOPE_PASS" | tee -a "$OUT/stages.log"
echo CH03_39_REAL_TTY_AND_ROS_TOPICS_PASS_GAZEBO_NOT_RUN | tee "$OUT/verdict.txt"
