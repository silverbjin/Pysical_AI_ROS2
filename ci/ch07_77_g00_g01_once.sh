#!/usr/bin/env bash
# Ch07 #173 G00+G01 only. No Gazebo, MoveIt or physical actuation.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch07-77-g01"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=77 ROS_LOCALHOST_ONLY=1 DEBIAN_FRONTEND=noninteractive
export CH07_77_G01_RECEIPT="$OUT/g01_ros_receipt.json"
NODE_PID=
STAGE=INIT
stage(){ STAGE="$1"; printf 'STAGE=%s\n' "$STAGE" | tee -a "$OUT/stages.log"; }
cleanup(){
  local rc="$?" shutdown="NO_NODE"
  trap - EXIT
  set +e
  if [[ -n "$NODE_PID" ]]; then
    shutdown=TERM_REQUESTED
    kill -TERM -- "-$NODE_PID" 2>/dev/null || true
    local attempt
    for attempt in $(seq 1 40); do
      if ! ps -eo pgid=,stat= | awk -v pg="$NODE_PID" '$1==pg && $2 !~ /^Z/ {a=1} END {exit !a}'; then
        shutdown=TERM_CLEAN; break
      fi
      sleep .15
    done
    if [[ "$shutdown" != TERM_CLEAN ]]; then
      kill -KILL -- "-$NODE_PID" 2>/dev/null || true
      shutdown=SIGKILL_ESCALATION
      [[ "$rc" -ne 0 ]] || rc=75
    fi
    wait "$NODE_PID" 2>/dev/null || true
  fi
  printf '{"stage":"%s","exit_code":%d,"shutdown":"%s","scope":"G00_G01_ONLY_NO_GAZEBO_NO_MOVEIT","ch10":"HOLD"}\n' \
   "$STAGE" "$rc" "$shutdown" > "$OUT/result.json"
  echo "CH07_77_G01_FINAL rc=$rc shutdown=$shutdown stage=$STAGE"
  exit "$rc"
}
trap cleanup EXIT
cd "$ROOT"
stage STATIC_G00_ASSERTIONS
python3 -m py_compile ci/ch07_77_g00_preflight.py ci/ch07_77_g01_ros_probe.py \
 Ch07/ros2_ws/src/vision_basics/vision_basics/mission_controller.py \
 Ch07/ros2_ws/src/vision_basics/vision_basics/mission_target_gate.py
python3 ci/ch07_77_g00_preflight.py --out "$OUT/g00_static.json" > "$OUT/g00_preflight.log"
stage PURE_TARGET_GATE_TESTS
python3 -m unittest discover -s ci/tests -p 'test_ch07_77_target_gate.py' -v \
 > "$OUT/unit_tests.log" 2>&1
grep -q 'OK' "$OUT/unit_tests.log"
stage BUILD_ONLY_CHANGED_VISION_PACKAGE
cd "$ROOT/Ch07/ros2_ws"
timeout --signal=TERM --kill-after=8s 90s colcon build --symlink-install --packages-select vision_basics \
 > "$OUT/colcon.log" 2>&1
set +u; source "$PWD/install/setup.bash"; set -u
ros2 pkg executables vision_basics > "$OUT/installed_executables.txt"
grep -q '^vision_basics mission_controller$' "$OUT/installed_executables.txt"
stage EXPAND_COMBINED_CAMERA_ARM_GRIPPER_XACRO
xacro "$(ros2 pkg prefix --share vision_basics)/urdf/my_robot.pick_gazebo.urdf.xacro" \
 > "$OUT/combined_robot.urdf" 2> "$OUT/xacro_stderr.txt"
python3 "$ROOT/ci/ch07_77_g00_preflight.py" --expanded "$OUT/combined_robot.urdf" \
 --out "$OUT/g00_expanded.json" >> "$OUT/g00_preflight.log"
stage START_REAL_ROS_G01_MISSION_ADMISSION_ONLY
setsid ros2 run vision_basics mission_controller \
 --ros-args -p use_sim_time:=false > "$OUT/mission.log" 2>&1 &
NODE_PID="$!"
stage ACTUAL_ROS_DDS_INPUT_AND_ZERO_GOAL_WITNESS
timeout --signal=TERM --kill-after=8s 70s \
 python3 "$ROOT/ci/ch07_77_g01_ros_probe.py" > "$OUT/g01_probe.log" 2>&1
grep -q CH07_77_G01_REAL_ROS_3D_STABLE_TARGET_AND_ZERO_MOTION_SCOPED_PASS "$OUT/g01_probe.log"
grep -q CH07_77_G01_REAL_ROS_STABLE_TARGET_READY_NO_GOAL "$OUT/mission.log"
stage INDEPENDENT_RECEIPT_AUDIT
python3 - "$OUT/g01_ros_receipt.json" "$OUT/g00_expanded.json" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
g=json.loads(Path(sys.argv[2]).read_text())
assert r["status"]=="SCOPED_PASS" and r["scope"].endswith("NO_GOALS")
assert r["invalid_count"]==7 and r["actual_ros_ready_count"]==1
assert r["actual_ros_pregrasp_candidates"]==1 and r["one_shot"]
assert r["arm_goals"]==r["gripper_goals"]==0 and r["moveit"]=="NOT_RUN"
assert g["status"]=="STATIC_PASS" and g["expanded_urdf"]=="PASS"
assert g["physical_runtime"]=="NOT_RUN" and r["ch10"]=="HOLD"
print("CH07_77_G00_G01_INDEPENDENT_SCOPED_RECEIPT_PASS")
PY
stage G00_G01_SCOPED_PASS_G02_G03_G04_NOT_RUN
echo CH07_77_G00_G01_REAL_ROS_FAIL_CLOSED_ADMISSION_SCOPED_PASS_NO_MOTION | tee "$OUT/verdict.txt"
