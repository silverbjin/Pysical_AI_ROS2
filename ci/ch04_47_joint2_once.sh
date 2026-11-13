#!/usr/bin/env bash
# Ch04 §4.7: CH03's actual ROS->GZ joint2 path and real Gazebo physics.
# The Ch04 original executable joint_position_cli is absent; don't invent it.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work;OUT="$ROOT/ci-results/ch04-47";mkdir -p "$OUT"
export ROS_DOMAIN_ID=47 ROS_LOCALHOST_ONLY=1 PYTHONUNBUFFERED=1
export GZ_PARTITION="ch04_47-${GITHUB_RUN_ID:-local}-$$-${RANDOM}"
export GZ_IP=127.0.0.1 QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1
OWNED=();STAGE=INIT
stage(){ STAGE="$1";echo "STAGE=$1" | tee -a "$OUT/stages.log"; }
start(){
 local name="$1";shift
 setsid "$@" > "$OUT/$name.log" 2>&1 &
 OWNED+=("$!")
 echo "START:$name:$!" | tee -a "$OUT/stages.log"
}
stop_group(){
 local pid="$1"
 kill -TERM -- "-$pid" 2>/dev/null || true
 local attempt state
 for attempt in $(seq 1 18); do
   state="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
   if [[ -z "$state" || "$state" == Z* ]]; then
     wait "$pid" 2>/dev/null || true
     return 0
   fi
   sleep .15
 done
 kill -KILL -- "-$pid" 2>/dev/null || true
 wait "$pid" 2>/dev/null || true
 echo "CH04_47_SIGKILL_ESCALATED_PGID=$pid" >> "$OUT/stages.log"
 return 1
}
cleanup(){
 local rc="$?";trap - EXIT;set +e
 local idx shutdown=SIGTERM_OWNED_GROUPS
 for ((idx=${#OWNED[@]}-1;idx>=0;idx--)); do
   stop_group "${OWNED[$idx]}" || shutdown=SIGKILL_ESCALATION
 done
 if [[ "$shutdown" == SIGKILL_ESCALATION && "$rc" == 0 ]]; then rc=75; fi
 printf '{"chapter":"Ch04","section":"4.7","exit_code":%d,"stage":"%s","shutdown":"%s","status":"%s","original_ch04_executable":"NOT_IMPLEMENTED","ch10":"HOLD"}\n' \
 "$rc" "$STAGE" "$shutdown" "$([[ "$rc" == 0 ]] && echo SCOPED_PASS || echo FAIL)" > "$OUT/result.json"
 echo "CH04_47_SHUTDOWN=$shutdown rc=$rc" | tee -a "$OUT/stages.log"
 exit "$rc"
}
trap cleanup EXIT
printf 'source_sha=%s\n' "${RUN_SOURCE_SHA:-UNKNOWN}" > "$OUT/environment.txt"
stage BUILD_CH03_ORIGINAL_PACKAGE_ONLY
WS="$ROOT/Ch03/ros2_ws"
cd "$WS"
timeout --signal=TERM --kill-after=7s 120s \
 colcon build --symlink-install --packages-select my_robot_description \
 > "$OUT/colcon.log" 2>&1
set +u;source install/setup.bash;set -u
ros2 pkg executables my_robot_description | tee "$OUT/executables.txt"
grep -q 'my_robot_description joint_control_cli' "$OUT/executables.txt"
stage PARSE_ORIGINAL_GAZEBO_ARM_MODEL
xacro "$WS/src/my_robot_description/urdf/two_dof_arm.urdf.xacro" > "$OUT/robot.urdf"
check_urdf "$OUT/robot.urdf" > "$OUT/urdf_check.txt"
grep -q 'joint2' "$OUT/urdf_check.txt"
python3 - "$OUT/robot.urdf" "$OUT/rsp.yaml" <<'PY'
from pathlib import Path
import sys,yaml
xml=Path(sys.argv[1]).read_text()
Path(sys.argv[2]).write_text(yaml.safe_dump(
 {"robot_state_publisher":{"ros__parameters":{
  "robot_description":xml,"use_sim_time":True
 } }},sort_keys=False))
PY
stage REAL_ROBOT_STATE_PUBLISHER
start rsp ros2 run robot_state_publisher robot_state_publisher \
 --ros-args --params-file "$OUT/rsp.yaml"
stage START_PREEXISTING_GAZEBO_WORLD
start gz_server gz sim -s -r -v 2 "$WS/src/my_robot_description/worlds/my_world.sdf"
READY=0
for attempt in $(seq 1 30); do
  if timeout 3s gz service -l 2>/dev/null | grep -Fq \
    '/world/my_first_world/create';then READY=1;break;fi
  sleep .5
done
[[ "$READY" == 1 ]] || { echo CH04_47_GAZEBO_WORLD_NOT_READY;exit 3; }
stage ORIGINAL_ROS_GAZEBO_BRIDGE
start bridge ros2 run ros_gz_bridge parameter_bridge \
 --ros-args -p config_file:="$WS/src/my_robot_description/config/ros_gz_bridge.yaml"
stage SPAWN_REAL_CH03_MODEL_WITH_ORIGINAL_NAME
timeout --signal=TERM --kill-after=5s 40s \
 ros2 run ros_gz_sim create -world my_first_world \
 -name my_robot -file "$OUT/robot.urdf" -z 0.1 \
 2>&1 | tee "$OUT/spawn.log"
grep -q 'Entity creation successful' "$OUT/spawn.log"
stage REAL_SIM_CLOCK_AND_JOINT_STATE_CHANNELS
timeout 15s ros2 topic info -v /joint2/cmd_pos > "$OUT/command_topic.txt"
timeout 15s ros2 topic info -v /joint_states > "$OUT/state_topic.txt"
timeout 18s ros2 topic echo /clock --once > "$OUT/clock.txt" 2>&1
grep -q 'sec:' "$OUT/clock.txt"
stage START_ORIGINAL_CH03_JOINT_CONTROL_CLI
# Original CLI targets joint2  -0.785,+0.785,... at 2-second intervals.
start joint_control_cli ros2 run my_robot_description joint_control_cli
stage INDEPENDENT_REAL_GAZEBO_PHYSICAL_JOINT2_FEEDBACK
timeout --signal=TERM --kill-after=5s 25s \
 python3 "$ROOT/ci/ch04_47_joint2_probe.py" "$OUT/physical_receipt.json" \
 2>&1 | tee "$OUT/physical_probe.log"
grep -q CH04_47_REAL_GAZEBO_JOINT2_COMMAND_TO_MEASURED_REVERSAL_PASS \
 "$OUT/physical_probe.log"
stage CH04_47_GAZEBO_JOINT2_SCOPED_PASS
echo CH04_47_REAL_BRIDGED_JOINT2_PHYSICAL_RESPONSE_PASS_GUI_NOT_RUN \
 | tee "$OUT/verdict.txt"
