#!/usr/bin/env bash
# Ch07 #173 G03A: REAL MoveIt GetPositionIK + MoveGroup plan_only.
# G02 previous accepted real camera target replay only. ZERO motion GOALS.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash;set -u
ROOT=/work;OUT="$ROOT/ci-results/ch07-77-g03a"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=79 ROS_LOCALHOST_ONLY=1 GZ_IP=127.0.0.1
export GZ_PARTITION="ch07_77_g03a_${GITHUB_RUN_ID:-local}_$$_$RANDOM"
export DEBIAN_FRONTEND=noninteractive
export CH07_77_G03_RECEIPT="$OUT/g03_plan_receipt.json"
export CH07_77_G02_FROZEN_TARGET="$ROOT/ci/docker/fixtures/ch07_77_g03_frozen_g02_target.json"
STAGE=INIT; OWNED=();NAMES=()
stage(){ STAGE="$1";echo "STAGE=$STAGE" |tee -a "$OUT/stages.log"; }
start(){
 local name="$1";shift
 setsid "$@" > "$OUT/$name.log" 2>&1 &
 OWNED+=("$!");NAMES+=("$name")
 echo "START:$name:pgid=$!" >> "$OUT/stages.log"
}
running(){
 local pg="$1"
 ps -eo pgid=,stat=|awk -v pg="$pg" '$1==pg && $2 !~ /^Z/ {yes=1} END {exit !yes}'
}
cleanup(){
 local rc="$?" shutdown="OWNED_GROUPS_EXITED_NO_SIGKILL" idx attempt pg
 trap - EXIT;set +e
 for ((idx=${#OWNED[@]}-1;idx>=0;idx--));do
   pg="${OWNED[$idx]}"
   if ! running "$pg";then wait "$pg" 2>/dev/null || true;continue;fi
   kill -TERM -- "-$pg" 2>/dev/null || true
   for attempt in $(seq 1 60);do
     running "$pg"||break
     sleep .15
   done
   if running "$pg";then
     kill -KILL -- "-$pg" 2>/dev/null || true
     shutdown="SIGKILL_ESCALATION"
     [[ "$rc" -ne 0 ]]||rc=75
   fi
   wait "$pg" 2>/dev/null || true
 done
 python3 - "$OUT/result.json" "$STAGE" "$rc" "$shutdown" <<'PY'
from pathlib import Path
import json,sys
p,stage,rc,shutdown=sys.argv[1:]
Path(p).write_text(json.dumps({
 "scope":"G03A_5DOF_MOVEIT_PLAN_ONLY_GAZEBO_TRUE_JOINT_STATES",
 "status":"SCOPED_PASS" if int(rc)==0 else "FAIL",
 "rc":int(rc),"stage":stage,"shutdown":shutdown,
 "G02":"REPLAY_ACCEPTED_ARTIFACT_NOT_RERUN",
 "G03B_execution":"NOT_RUN","G04_grasp":"NOT_RUN","Ch10":"HOLD"
},indent=2)+"\n")
PY
 echo "CH07_77_G03A_FINAL rc=$rc stage=$STAGE shutdown=$shutdown"
 exit "$rc"
}
trap cleanup EXIT
stage INSTALL_ONLY_MISSING_MOVEIT_JAZZY_DEPENDENCIES
packages=(
  ros-jazzy-moveit-configs-utils
  ros-jazzy-moveit-planners-ompl
  ros-jazzy-moveit-simple-controller-manager
  ros-jazzy-moveit-kinematics
  ros-jazzy-moveit-ros-move-group
  ros-jazzy-moveit-msgs
  ros-jazzy-gz-ros2-control
  ros-jazzy-controller-manager ros-jazzy-ros2controlcli
  ros-jazzy-joint-trajectory-controller ros-jazzy-joint-state-broadcaster
  ros-jazzy-ros2-control ros-jazzy-robot-state-publisher
  ros-jazzy-xacro ros-jazzy-control-msgs
)
missing=()
for p in "${packages[@]}";do dpkg -s "$p" >/dev/null 2>&1||missing+=("$p");done
if (("${#missing[@]}"));then
 timeout --signal=TERM --kill-after=10s 100s apt-get update -qq >"$OUT/apt_update.log" 2>&1
 timeout --signal=TERM --kill-after=12s 240s apt-get install -y --no-install-recommends "${missing[@]}" >"$OUT/apt_install.log" 2>&1
fi
dpkg-query -W "${packages[@]}" > "$OUT/versions.txt"
set +u;source /opt/ros/jazzy/setup.bash;set -u
stage BUILD_ONLY_CH07_COMPOSED_ROBOT_AND_MOVEIT_CONFIG
cd "$ROOT/Ch07/ros2_ws"
timeout --signal=TERM --kill-after=8s 130s colcon build --symlink-install \
  --packages-select vision_basics my_robot_moveit_config >"$OUT/colcon.log" 2>&1
set +u;source "$PWD/install/setup.bash";set -u
stage EXPAND_SAME_ORIGINAL_ROBOT_5_ARM_2_FINGER_GAZEBO_URDF
xacro "$(ros2 pkg prefix --share vision_basics)/urdf/my_robot.pick_gazebo.urdf.xacro" > "$OUT/robot.urdf"
check_urdf "$OUT/robot.urdf" >"$OUT/check_urdf.log"
python3 "$ROOT/ci/ch07_77_g00_preflight.py" --expanded "$OUT/robot.urdf" \
  --out "$OUT/g00_expanded.json" > "$OUT/g00.log"
python3 "$ROOT/ci/ch07_77_g03_moveit_params.py" \
  --robot "$OUT/robot.urdf" --out "$OUT/move_group.yaml" \
  --receipt "$OUT/g03_params.json" >"$OUT/config.log"
python3 - "$OUT/robot.urdf" "$OUT/rsp.yaml" <<'PY'
from pathlib import Path
import yaml,sys
xml=Path(sys.argv[1]).read_text()
Path(sys.argv[2]).write_text(yaml.safe_dump({
 "robot_state_publisher":{"ros__parameters":{
 "robot_description":xml,"use_sim_time":True
 }}},sort_keys=False))
PY
stage START_ORIGINAL_REAL_GAZEBO_WITH_GAZEBO_SIM_SYSTEM
start rsp ros2 run robot_state_publisher robot_state_publisher \
 --ros-args --params-file "$OUT/rsp.yaml"
start gazebo gz sim -s -r -v 3 empty.sdf
READY=0
for attempt in $(seq 1 55);do
 if timeout 4s gz service -l 2>/dev/null |grep -Fq '/world/empty/create';then
 READY=1;break;fi
 sleep .3
done
[[ "$READY" -eq 1 ]] || { echo G03A_REAL_WORLD_NOT_READY;exit 3; }
stage SPAWN_IDENTICAL_GAZEBO_URDF
timeout --signal=TERM --kill-after=5s 50s ros2 run ros_gz_sim create \
 -world empty -name my_robot -file "$OUT/robot.urdf" -z .05 >"$OUT/create.log" 2>&1
grep -q 'Entity creation successful' "$OUT/create.log"
stage REAL_ROS_CLOCK_AND_JOINT_STATE
start bridge ros2 run ros_gz_bridge parameter_bridge '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
timeout --signal=TERM --kill-after=5s 60s ros2 run controller_manager spawner \
 joint_state_broadcaster --controller-manager /controller_manager \
 --controller-manager-timeout 50 >"$OUT/jsb.log" 2>&1
timeout --signal=TERM --kill-after=5s 60s ros2 run controller_manager spawner \
 arm_group_controller --controller-manager /controller_manager \
 --controller-manager-timeout 50 >"$OUT/arm_spawner.log" 2>&1
timeout --signal=TERM --kill-after=5s 60s ros2 run controller_manager spawner \
 gripper_group_controller --controller-manager /controller_manager \
 --controller-manager-timeout 50 >"$OUT/gripper_spawner.log" 2>&1
timeout 12s ros2 control list_hardware_components -c /controller_manager >"$OUT/hardware.log"
grep -q GazeboSimSystem "$OUT/hardware.log"
! grep -q FakeSystem "$OUT/hardware.log"
timeout 12s ros2 control list_controllers -c /controller_manager >"$OUT/controllers.log"
grep -q 'arm_group_controller.*active' "$OUT/controllers.log"
grep -q 'gripper_group_controller.*active' "$OUT/controllers.log"
grep -q 'joint_state_broadcaster.*active' "$OUT/controllers.log"
timeout 12s ros2 topic echo /joint_states --once >"$OUT/joints_before.log"
stage START_REAL_MOVEIT_MOVE_GROUP_FROM_IDENTICAL_GAZEBO_DESCRIPTION
start move_group ros2 run moveit_ros_move_group move_group \
 --ros-args --params-file "$OUT/move_group.yaml"
stage ACTUAL_KDL_IK_AND_MOVEGROUP_OMPL_PLAN_ONLY_NO_ACTUATION
timeout --signal=TERM --kill-after=10s 135s \
 python3 "$ROOT/ci/ch07_77_g03_plan_only_probe.py" >"$OUT/g03_probe.log" 2>&1
grep -q CH07_77_G03A_ACTUAL_MOVEIT_5DOF_G02_TARGET_DERIVED_PLAN_ONLY_ZERO_MOTOR_COMMANDS_SCOPED_PASS "$OUT/g03_probe.log"
stage INDEPENDENT_REAL_MOVEIT_PLAN_ONLY_RECEIPT
python3 - "$OUT/g03_plan_receipt.json" "$OUT/g03_params.json" <<'PY'
from pathlib import Path
import json,sys
r=json.loads(Path(sys.argv[1]).read_text())
p=json.loads(Path(sys.argv[2]).read_text())
assert r["status"]=="SCOPED_PASS" and r["plan_only_succeeded"]
assert r["arm_controller_topic_count"]==0 and r["arm_goal_execution_count"]==0
assert r["G02_live_rgbd_in_this_run"]=="NOT_RUN_ACCEPTED_G02_REPLAY_ONLY"
assert r["moveit_execute"]=="NOT_RUN" and r["G04_physical_grasp"]=="NOT_RUN"
assert p["status"]=="STATIC_PASS" and p["gazebo_urdf_exact_bytes"]
assert r["ch10"]==p["Ch10"]=="HOLD"
print("CH07_77_G03A_INDEPENDENT_IK_PLAN_ONLY_ZERO_MOTION_RECEIPT_PASS")
PY
stage G03A_TARGET_DERIVED_KDL_OMPL_PLAN_ONLY_SCOPED_PASS
echo CH07_77_G03A_MEASURED_G02_TARGET_REPLAY_REAL_MOVEIT_PLAN_ONLY_SCOPED_PASS >"$OUT/verdict.txt"
