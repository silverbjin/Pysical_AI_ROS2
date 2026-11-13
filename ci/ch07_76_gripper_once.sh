#!/usr/bin/env bash
# Ch07 §7.6 original gripper controller against actual GazeboSimSystem.
# Simulated joint motion only, not object grasp/physical contacts.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work; OUT="$ROOT/ci-results/ch07-76"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=76 ROS_LOCALHOST_ONLY=1 GZ_IP=127.0.0.1
export GZ_PARTITION="book_ch07_76_${RUN_SOURCE_SHA:-local}_$$"
export QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1 DEBIAN_FRONTEND=noninteractive
printf 'tested_sha=%s\nimage=%s\nROS_DOMAIN_ID=%s\nGZ_PARTITION=%s\n' \
 "${RUN_SOURCE_SHA:-UNKNOWN}" \
 'ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f' \
 "$ROS_DOMAIN_ID" "$GZ_PARTITION" > "$OUT/environment.txt"
OWNED=(); STAGE=INIT
stage(){ STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
start(){
 local name="$1"; shift
 # Separate process groups: gz sim and ros2 run can spawn grandchildren.
 setsid "$@" > "$OUT/$name.log" 2>&1 &
 OWNED+=("$!")
 echo "START:$name:pgid=$!" | tee -a "$OUT/stages.log"
}
log_shutdown(){
  # No tee pipeline in teardown: it can retain the Docker stdout pipe.
  printf '%s\n' "$1" >> "$OUT/teardown_trace.log"
  printf '%s\n' "$1" >&2
}
stop_owned(){
 local pgid="$1"
 # Bash functions have dynamic scope: never reuse cleanup()'s loop index.
 local attempt
 log_shutdown "CH07_76_STOP_START_PGID=$pgid"
 # Actual descendant process group. Reaping remains delegated to Docker --init.
 kill -TERM -- "-$pgid" 2>/dev/null || true
 for attempt in $(seq 1 12); do
   if ! kill -0 -- "-$pgid" 2>/dev/null; then
     log_shutdown "CH07_76_STOP_TERM_EXIT_PGID=$pgid"
     return 0
   fi
   sleep 0.2
 done
 log_shutdown "CH07_76_STOP_SIGKILL_ESCALATION_PGID=$pgid"
 kill -KILL -- "-$pgid" 2>/dev/null || true
 return 1
}
cleanup(){
 local code="$?"
 trap - EXIT
 set +e
 log_shutdown "CH07_76_EXIT_TRAP_ENTER code=$code owned_groups=${#OWNED[@]}"
 # Preserve the real relationship between Docker PID1, Gazebo subprocesses
 # and each PGID even when an external timeout later kills the container.
 ps -eo pid,ppid,pgid,sid,stat,comm > "$OUT/teardown_ps_before.txt" 2>&1
 local shutdown=PROCESS_GROUPS_EXITED_AFTER_SIGTERM
 local i
 for ((i=${#OWNED[@]}-1;i>=0;i--)); do
   log_shutdown "CH07_76_STOP_INDEX=$i PID=${OWNED[$i]}"
   if ! stop_owned "${OWNED[$i]}"; then
     shutdown=SIGKILL_ESCALATED
   fi
   log_shutdown "CH07_76_STOP_FINISHED_INDEX=$i"
 done
 ps -eo pid,ppid,pgid,sid,stat,comm > "$OUT/teardown_ps_after.txt" 2>&1
 log_shutdown "CH07_76_TEARDOWN_ALL_GROUPS_PROCESSED status=$shutdown"
 if [[ "$shutdown" == SIGKILL_ESCALATED && "$code" -eq 0 ]]; then
   code=75
 fi
 local scope=SCOPED_PASS
 if [[ "${CH07_76_TEARDOWN_ONLY:-0}" == 1 ]]; then
   scope=TEARDOWN_SCOPE_PASS
 fi
 local status=FAIL
 if [[ "$code" == 0 ]]; then
   status=$scope
 fi
 printf '{"status":"%s","rc":%d,"stage":"%s","shutdown":"%s","action_retest":"%s","object_grasp":"NOT_RUN","camera":"BLOCKED_127","ch10":"HOLD"}\n' \
  "$status" "$code" "$STAGE" "$shutdown" \
  "$([[ "${CH07_76_TEARDOWN_ONLY:-0}" == 1 ]] && echo NOT_RUN || echo RUN)" \
  > "$OUT/result.json"
 log_shutdown "CH07_76_SHUTDOWN=$shutdown rc=$code"
 exit "$code"
}
trap cleanup EXIT
stage CHECK_PINNED_IMAGE_AND_GAZEBO_CONTROL_DEPS
packages=(ros-jazzy-gz-ros2-control ros-jazzy-controller-manager
  ros-jazzy-joint-trajectory-controller ros-jazzy-joint-state-broadcaster
  ros-jazzy-ros2controlcli ros-jazzy-ros2-control
  ros-jazzy-robot-state-publisher ros-jazzy-xacro ros-jazzy-control-msgs)
missing=()
for p in "${packages[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
if ((${#missing[@]})); then
 timeout --signal=TERM --kill-after=10s 110s apt-get update -qq > "$OUT/apt_update.log" 2>&1
 timeout --signal=TERM --kill-after=12s 225s apt-get install -y --no-install-recommends \
   "${missing[@]}" > "$OUT/apt_install.log" 2>&1
fi
dpkg-query -W "${packages[@]}" > "$OUT/installed_versions.txt"
set +u; source /opt/ros/jazzy/setup.bash; set -u
stage BUILD_ORIGINAL_CH07_VISION_BASICS_ONLY
cd "$ROOT/Ch07/ros2_ws"
timeout --signal=TERM --kill-after=10s 110s colcon build --symlink-install \
 --packages-select vision_basics > "$OUT/colcon.log" 2>&1
set +u; source "$PWD/install/setup.bash"; set -u
ros2 pkg executables vision_basics > "$OUT/executables.txt"
grep -q 'vision_basics gripper_controller' "$OUT/executables.txt"
python3 -m py_compile src/vision_basics/vision_basics/gripper_controller.py
stage ORIGINAL_FINGER_URDF_AND_GAZEBO_PLUGIN_CONTRACT
xacro "$(ros2 pkg prefix --share vision_basics)/urdf/my_robot.gripper_gazebo.urdf.xacro" \
  > "$OUT/gripper.urdf"
check_urdf "$OUT/gripper.urdf" > "$OUT/urdf_report.txt"
grep -q 'gz_ros2_control/GazeboSimSystem' "$OUT/gripper.urdf"
grep -q 'gz_ros2_control::GazeboSimROS2ControlPlugin' "$OUT/gripper.urdf"
grep -q 'name="joint_finger1"' "$OUT/gripper.urdf"
grep -q 'name="joint_finger2"' "$OUT/gripper.urdf"
# A commented legacy Xacro contains the word FakeSystem. Do not mistake
# that comment for the active hardware: assert actual GazeboSimSystem below
# using ros2 control list_hardware_components after the live plugin loads.
python3 - "$OUT/gripper.urdf" "$OUT/rsp.yaml" <<'PY'
from pathlib import Path
import sys,yaml
xml=Path(sys.argv[1]).read_text()
Path(sys.argv[2]).write_text(yaml.safe_dump({
  "robot_state_publisher":{"ros__parameters":{
     "robot_description":xml,"use_sim_time":True
  }}
},sort_keys=False))
PY
stage RSP_THEN_EXISTING_GAZEBO_HARMONIC_EMPTY_WORLD
start rsp ros2 run robot_state_publisher robot_state_publisher \
 --ros-args --params-file "$OUT/rsp.yaml"
start gazebo gz sim -s -r -v 2 empty.sdf
READY=0
for _ in $(seq 1 45); do
  if timeout 4s gz service -l 2>/dev/null | grep -Fq '/world/empty/create'; then
    READY=1;break
  fi
  sleep .4
done
[[ "$READY" == 1 ]] || { echo CH07_76_GAZEBO_WORLD_NOT_READY; exit 5; }
stage SPAWN_EXISTING_CH07_ROBOT_WITH_GAZEBO_SYSTEM
timeout --signal=TERM --kill-after=5s 48s ros2 run ros_gz_sim create \
 -world empty -name my_robot -file "$OUT/gripper.urdf" -z 0.05 \
 2>&1 | tee "$OUT/create.log"
grep -q 'Entity creation successful' "$OUT/create.log"
start bridge ros2 run ros_gz_bridge parameter_bridge \
 '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
stage SPAWN_ORIGINAL_TWO_FINGER_TRAJECTORY_CONTROLLER
timeout --signal=TERM --kill-after=5s 56s ros2 run controller_manager spawner \
 joint_state_broadcaster --controller-manager /controller_manager \
 --controller-manager-timeout 45 > "$OUT/jsb_spawner.log" 2>&1
timeout --signal=TERM --kill-after=5s 56s ros2 run controller_manager spawner \
 gripper_group_controller --controller-manager /controller_manager \
 --controller-manager-timeout 45 > "$OUT/gripper_spawner.log" 2>&1
timeout 12s ros2 control list_controllers -c /controller_manager \
 > "$OUT/controllers.txt" 2>&1
grep -q 'joint_state_broadcaster.*active' "$OUT/controllers.txt"
grep -q 'gripper_group_controller.*active' "$OUT/controllers.txt"
timeout 12s ros2 control list_hardware_components -c /controller_manager \
 > "$OUT/hardware.txt" 2>&1
grep -q GazeboSimSystem "$OUT/hardware.txt"
! grep -q FakeSystem "$OUT/hardware.txt"
timeout 12s ros2 action list -t > "$OUT/actions.txt"
grep -Fq '/gripper_group_controller/follow_joint_trajectory [control_msgs/action/FollowJointTrajectory]' "$OUT/actions.txt"
timeout 12s ros2 topic echo /joint_states --once > "$OUT/joints_before.txt"
if [[ "${CH07_76_TEARDOWN_ONLY:-0}" == 1 ]]; then
  stage CH07_76_TERMINATION_ONLY_NO_ACTION_RETEST
  echo 'CH07_76_GAZEBO_CONTROLLERS_READY_FOR_OWNED_PROCESS_GROUP_SHUTDOWN' | tee "$OUT/verdict.txt"
  # Enter cleanup explicitly, before any shell exit bookkeeping.
  cleanup
fi
stage ORIGINAL_GRIPPER_OPEN_RESULT_THEN_CLOSE_RESULT
timeout --signal=TERM --kill-after=5s 48s ros2 run vision_basics gripper_controller \
 2>&1 | tee "$OUT/gripper_cli.log"
for m in CH07_76_REAL_JOINT_STATE_STREAM_READY \
 CH07_76_OPEN_ACTION_AND_MEASURED_JOINTS_PASS \
 CH07_76_CLOSE_ACTION_AND_MEASURED_JOINTS_PASS \
 CH07_76_SEQUENCE_OPEN_RESULT_THEN_CLOSE_REAL_FEEDBACK_PASS
do grep -q "$m" "$OUT/gripper_cli.log"; done
stage INDEPENDENT_SECOND_SUBSCRIBER_AND_RECEIPT
export CH07_76_RECEIPT="$OUT/gripper_joint_receipt.json"
timeout --signal=TERM --kill-after=5s 30s python3 "$ROOT/ci/ch07_76_gripper_witness.py" \
 "$OUT/gripper_cli.log" 2>&1 | tee "$OUT/witness.log"
grep -q CH07_76_INDEPENDENT_REAL_GAZEBO_FINGER_ACTION_AND_FINAL_JOINTS_PASS "$OUT/witness.log"
stage CH07_76_SCOPED_PASS
echo 'CH07_76_ACTUAL_GAZEBO_TWO_FINGER_ACTION_AND_MEASURED_JOINTS_PASS_NO_OBJECT' \
 | tee "$OUT/verdict.txt"
