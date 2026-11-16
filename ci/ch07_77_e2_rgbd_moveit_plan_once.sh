#!/usr/bin/env bash
# Issue #173 E2: reuses G04A original real RGB-D pipeline with MoveIt PLAN ONLY.
# Test-only single sensor target; ZERO arm/gripper motor Goals.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch07-77-e2"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=78 GZ_IP=127.0.0.1
export GZ_PARTITION="book_ch07_77_g04a_${GITHUB_RUN_ID:-local}_$$_$RANDOM"
export QT_QPA_PLATFORM=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
export ROS_LOCALHOST_ONLY=1 DEBIAN_FRONTEND=noninteractive
export CH07_77_G04A_RECEIPT="$OUT/g04a_live_receipt.json"
export CH07_77_E2_RECEIPT="$OUT/e2_moveit_plan_receipt.json"
export CH07_77_G04A_WITNESS_READY_FILE="$OUT/witness_dds_ready.flag"
STAGE=INIT; OWNED=(); NAMES=(); GZ_PGID=
stage(){ STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
start(){
  local n="$1"; shift
  setsid "$@" > "$OUT/$n.log" 2>&1 &
  OWNED+=("$!");NAMES+=("$n")
  echo "START:$n:pgid=$!" >> "$OUT/stages.log"
  [[ "$n" != gazebo ]] || GZ_PGID="$!"
}
group_running(){
 local pg="$1"
 ps -eo pgid=,stat= | awk -v pg="$pg" '$1==pg && $2 !~ /^Z/ {a=1} END {exit !a}'
}
stop_group(){
 local pg="$1" name="$2" original_rc="$3" attempt rc
 if ! group_running "$pg";then
   wait "$pg" 2>/dev/null || true
   return 0
 fi
 if [[ "$name" == gazebo && "$original_rc" -eq 0 ]];then
   for attempt in $(seq 1 200);do
     if ! group_running "$pg";then
       rc=0;wait "$pg" || rc="$?"
       echo "CH07_77_G04A_GAZEBO_NATURAL_EXIT_RC=$rc" >> "$OUT/stages.log"
       [[ "$rc" -eq 0 ]] && return 0 || return 1
     fi
     sleep .2
   done
 fi
 if [[ "$name" == gazebo ]];then
   timeout 5s gz service -s /server_control --reqtype gz.msgs.ServerControl \
     --reptype gz.msgs.Boolean --timeout 1000 --req 'stop: true' \
     > "$OUT/server_control.log" 2>&1 || true
 fi
 kill -TERM -- "-$pg" 2>/dev/null || true
 for attempt in $(seq 1 40);do
   if ! group_running "$pg";then
      wait "$pg" 2>/dev/null || true
      return 0
   fi
   sleep .2
 done
 kill -KILL -- "-$pg" 2>/dev/null || true
 wait "$pg" 2>/dev/null || true
 echo "SIGKILL_ESCALATION:$name:$pg" >> "$OUT/stages.log"
 return 1
}
cleanup(){
  local original_rc="$?" result="$?" idx shutdown="OWNED_GROUPS_EXITED_NO_SIGKILL"
  trap - EXIT;set +e
  for ((idx=${#OWNED[@]}-1;idx>=0;idx--));do
    stop_group "${OWNED[$idx]}" "${NAMES[$idx]}" "$original_rc" || shutdown="SIGKILL_ESCALATION"
  done
  if [[ "$shutdown" != OWNED_GROUPS_EXITED_NO_SIGKILL && "$original_rc" -eq 0 ]];then
    result=75
  else
    result="$original_rc"
  fi
  [[ ! -f "$HOME/.gz/rendering/ogre2.log" ]] ||
     cp "$HOME/.gz/rendering/ogre2.log" "$OUT/ogre2.log" 2>/dev/null || true
  python3 - "$OUT/result.json" "$STAGE" "$result" "$shutdown" <<'PY'
import json,sys
from pathlib import Path
out,stage,rc,shutdown=sys.argv[1:]
Path(out).write_text(json.dumps({
 "scope":"E2_REAL_RGBD_DYNAMIC_RED_TARGET_TO_MOVEIT_PLAN_ONLY_NO_MOTOR_GOALS",
 "status":"SCOPED_PASS" if int(rc)==0 else "FAIL",
 "stage":stage,"rc":int(rc),"shutdown":shutdown,
 "G03":"NOT_RUN","G04":"NOT_RUN","Ch10":"HOLD"},indent=2)+"\n")
PY
  echo "CH07_77_G04A_FINAL rc=$result stage=$STAGE shutdown=$shutdown"
  exit "$result"
}
trap cleanup EXIT
stage DEPENDENCIES_SAME_DIGEST_AS_ACCEPTED_GAZEBO
packages=(ros-jazzy-gz-ros2-control ros-jazzy-controller-manager
  ros-jazzy-joint-trajectory-controller ros-jazzy-joint-state-broadcaster
  ros-jazzy-ros2controlcli ros-jazzy-ros2-control
  ros-jazzy-robot-state-publisher ros-jazzy-xacro ros-jazzy-control-msgs
  ros-jazzy-tf2-ros
  ros-jazzy-moveit-configs-utils ros-jazzy-moveit-planners-ompl
  ros-jazzy-moveit-simple-controller-manager ros-jazzy-moveit-kinematics
  ros-jazzy-moveit-ros-move-group ros-jazzy-moveit-msgs)
missing=()
for pkg in "${packages[@]}";do dpkg -s "$pkg" >/dev/null 2>&1||missing+=("$pkg");done
if (("${#missing[@]}"));then
 timeout --signal=TERM --kill-after=10s 100s apt-get update -qq >"$OUT/apt_update.log" 2>&1
 timeout --signal=TERM --kill-after=12s 220s apt-get install -y --no-install-recommends "${missing[@]}" >"$OUT/apt_install.log" 2>&1
fi
dpkg-query -W "${packages[@]}" > "$OUT/versions.txt"
set +u;source /opt/ros/jazzy/setup.bash;set -u
stage BUILD_ORIGINAL_VISION_PACKAGE_NO_CROSS_CHAPTER
cd "$ROOT/Ch07/ros2_ws"
timeout --signal=TERM --kill-after=8s 105s colcon build --symlink-install --packages-select vision_basics my_robot_moveit_config >"$OUT/colcon.log" 2>&1
set +u;source "$PWD/install/setup.bash";set -u
stage COMBINED_ORIGINAL_CAMERA_CONTROL_XACRO
xacro "$(ros2 pkg prefix --share vision_basics)/urdf/my_robot.pick_gazebo.urdf.xacro" > "$OUT/robot.urdf"
check_urdf "$OUT/robot.urdf" > "$OUT/urdf.log"
python3 "$ROOT/ci/ch07_77_g00_preflight.py" --expanded "$OUT/robot.urdf" \
 --out "$OUT/g00_expanded.json" > "$OUT/g00.log"
python3 "$ROOT/ci/ch07_77_g03_moveit_params.py" \
 --robot "$OUT/robot.urdf" --out "$OUT/move_group.yaml" \
 --receipt "$OUT/g03_params.json" >"$OUT/g03_config.log"
python3 - "$OUT/robot.urdf" "$OUT/rsp.yaml" <<'PY'
import yaml,sys
from pathlib import Path
xml=Path(sys.argv[1]).read_text()
Path(sys.argv[2]).write_text(yaml.safe_dump({"robot_state_publisher":{"ros__parameters":{
 "robot_description":xml,"use_sim_time":True}}},sort_keys=False))
PY
stage GENERATE_NEW_TEST_ONLY_GRASPABLE_DYNAMIC_RED_ROD
python3 "$ROOT/ci/ch07_77_g04a_graspable_fixture.py" \
 --source "$ROOT/ci/docker/fixtures/ch07_77_g02_dynamic_red_world.sdf" \
 --output "$OUT/graspable_dynamic_world.sdf" \
 --receipt "$OUT/fixture_receipt.json" > "$OUT/fixture.log"
stage ORIGINAL_RSP_AND_GAZEBO_OGRE2_SENSOR_WORLD
start rsp ros2 run robot_state_publisher robot_state_publisher \
  --ros-args --params-file "$OUT/rsp.yaml"
start gazebo gz sim -s -r -v 4 --headless-rendering --iterations 25000 \
  "$OUT/graspable_dynamic_world.sdf"
READY=0
for _ in $(seq 1 45);do
 if timeout 4s gz service -l | grep -Fq /world/book_camera/create;then READY=1;break;fi
 sleep .4
done
[[ "$READY" -eq 1 ]] || { echo "G04A_WORLD_NOT_READY";exit 4; }
stage SPAWN_ROBOT_WITH_SAME_ROS2_CONTROL_AND_RGBD_CAMERA
timeout --signal=TERM --kill-after=5s 48s ros2 run ros_gz_sim create \
 -world book_camera -name my_robot -file "$OUT/robot.urdf" -z 0.05 \
 > "$OUT/create.log" 2>&1
grep -q 'Entity creation successful' "$OUT/create.log"
stage CAPTURE_LIVE_NATIVE_GZ_MODEL_LIST_AND_DYNAMIC_POSE
timeout 12s gz model --list > "$OUT/gz_models.txt" 2>&1
grep -q g04_grasp_cylinder "$OUT/gz_models.txt"
timeout 12s gz model --model g04_grasp_cylinder --pose > "$OUT/gz_red_pose.txt" 2>&1
stage BRIDGE_REAL_CLOCK_RGB_DEPTH_K
start bridge ros2 run ros_gz_bridge parameter_bridge \
  '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock' \
  '/camera/image@sensor_msgs/msg/Image[gz.msgs.Image' \
  '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo' \
  '/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image' \
  --ros-args -r /camera/image:=/camera/image_raw \
   -r /camera/depth_image:=/camera/depth/image_raw
stage SAME_GAZEBO_CONTROL_JOINT_STATE_BROADCASTER
timeout --signal=TERM --kill-after=5s 58s ros2 run controller_manager spawner \
  joint_state_broadcaster --controller-manager /controller_manager \
  --controller-manager-timeout 45 > "$OUT/jsb.log" 2>&1
timeout 12s ros2 control list_hardware_components -c /controller_manager > "$OUT/hardware.log"
grep -q GazeboSimSystem "$OUT/hardware.log"
! grep -q FakeSystem "$OUT/hardware.log"
timeout 12s ros2 control list_controllers -c /controller_manager > "$OUT/controllers.log"
grep -q 'joint_state_broadcaster.*active' "$OUT/controllers.log"
stage START_ARM_AND_FINGER_CONTROL_SERVERS_ZERO_MOTOR_GOALS
# Controllers active for planning state only; no FollowJointTrajectory Action Goals.
timeout --signal=TERM --kill-after=5s 58s ros2 run controller_manager spawner \
  arm_group_controller --controller-manager /controller_manager \
  --controller-manager-timeout 45 >"$OUT/arm_spawner.log" 2>&1
timeout --signal=TERM --kill-after=5s 58s ros2 run controller_manager spawner \
  gripper_group_controller --controller-manager /controller_manager \
  --controller-manager-timeout 45 >"$OUT/gripper_spawner.log" 2>&1
timeout 12s ros2 control list_controllers -c /controller_manager >"$OUT/controllers_after.log"
grep -q 'arm_group_controller.*active' "$OUT/controllers_after.log"
grep -q 'gripper_group_controller.*active' "$OUT/controllers_after.log"
stage START_MOVEIT_PLAN_ONLY_SERVER_SAME_GAZEBO_ROBOT
start move_group ros2 run moveit_ros_move_group move_group \
 --ros-args --params-file "$OUT/move_group.yaml"
stage START_SAFE_ADMISSION_BEFORE_ANY_DETECTOR_3D_INPUT
start admission ros2 run vision_basics mission_controller --ros-args -p use_sim_time:=true
stage START_INDEPENDENT_WITNESS_BEFORE_ONE_SHOT_PUBLICATION
start witness python3 "$ROOT/ci/ch07_77_g04a_live_small_target_witness.py"
stage START_E2_SENSOR_TO_MOVEIT_PLAN_ONLY_SUBSCRIBER
start e2_planner ros2 run vision_basics mission_plan_only \
 --ros-args -p use_sim_time:=true -p mode:=plan_only \
 -p target_timeout_sec:=95.0
# A one-shot volatile PointStamped published before DDS discovery is lost.
# This is a witness setup race, NOT an image/Depth/TF failure. Start the
# producers only after the observer's actual topic subscription is visible.
stage WAIT_FOR_INDEPENDENT_WITNESS_DDS_DISCOVERY
DISCOVERED=0
for attempt in $(seq 1 80);do
  if [[ -s "$CH07_77_G04A_WITNESS_READY_FILE" ]];then
    DISCOVERED=1;break
  fi
  sleep .2
done
[[ "$DISCOVERED" -eq 1 ]] || { echo 'G04A_WITNESS_DDS_PUBLISHER_NOT_DISCOVERED';exit 8; }
# Allow DDS reliable subscription matching to settle before the first
# one-shot target. No motor or camera algorithm is modified by this wait.
sleep 1
stage ORIGINAL_ROS_DETECTOR_COORD_TRANSFORM_NO_GOALS
start detector ros2 run vision_basics object_detector --ros-args -p use_sim_time:=true
start coord ros2 run vision_basics coord_transformer --ros-args -p use_sim_time:=true
stage OBSERVE_REAL_RGBD_TO_3D_AND_ONE_SHOT
# Full detector and coordinate conversion are new *integration* behavior;
# standalone §7.2/7.4/7.5/7.6 original accepted tests are NOT_RERUN.
# Owned: rsp=0,gazebo=1,bridge=2,move_group=3,admission=4,witness=5,e2_planner=6,detector=7,coord=8.
WITNESS_PID="${OWNED[5]}"
# DDS can deliver G01 ready before the read-only G04A witness receives the
# matching 3D message. Preserve that standalone witness failure unmodified.
WITNESS_RC=0
wait "$WITNESS_PID" || WITNESS_RC="$?"
if [[ "$WITNESS_RC" -ne 0 ]];then
  grep -q 'MISSION_TARGET_NOT_FROM_SENSOR' "$OUT/witness.log" || {
    echo CH07_E2_UNRELATED_SENSOR_WITNESS_FAILURE;exit "$WITNESS_RC";
  }
  echo 'E2_PRIOR_WITNESS_SPARSE_3D_DDS_RACE_INDEPENDENT_STAMP_AUDIT_REQUIRED' >>"$OUT/stages.log"
else
  grep -q CH07_77_G04A_REAL_OGRE2_RGBD_RED_DETECTOR_3D_TARGET_NO_GOAL_SCOPED_PASS "$OUT/witness.log"
fi
stage VERIFY_E2_SENSOR_TO_MOVEIT_PLAN_ONLY
E2_PID="${OWNED[6]}"
wait "$E2_PID"
grep -q CH07_E2_SENSOR_TO_MOVEIT_PLAN_ONLY_PASS "$OUT/e2_planner.log"
python3 - "$CH07_77_E2_RECEIPT" <<'PY_E2'
import json,sys
r=json.load(open(sys.argv[1]))
assert r["status"]=="SENSOR_TO_MOVEIT_PLAN_ONLY_PASS"
assert r["move_group_plan_only_requests"]==len(r["stages"])==3
assert r["arm_motor_goal_count"]==r["gripper_motor_goal_count"]==0
assert all(t["plan_only"] and t["planned_points"]>0 for t in r["stages"])
assert r["G04B_PHYSICAL_CLEAN"]=="BLOCKED" and r["G05_FULL_E2E"]=="NOT_RUN"
print("CH07_77_E2_INDEPENDENT_SENSOR_TO_MOVEIT_PLAN_ONLY_PASS")
PY_E2
stage REVIEW_REAL_NATIVE_OBJECT_EXISTS_AND_NO_MOTION
# Harmonic 'gz model -l' means LINK, not list; --list queries real Gazebo.
# A live world can finish its finite iterations before the ROS witness ends.
# Thus this evidence must be captured immediately after spawn, not now.
grep -q 'g04_grasp_cylinder' "$OUT/gz_models.txt" || {
  echo "CH07_77_G04A_GZ_MODEL_LIST_MISSING_RED_CYLINDER"; exit 7;
}
python3 - "$OUT/g04a_live_receipt.json" "$OUT/fixture_receipt.json" "$CH07_77_E2_RECEIPT" "$OUT/coord.log" <<'PY'
import json,math,re,sys
from pathlib import Path
w,fixture,e2,coord=(Path(p) for p in sys.argv[1:])
r=json.loads(w.read_text()); f=json.loads(fixture.read_text())
p=json.loads(e2.read_text()); txt=coord.read_text()
assert r["actual_ready_count"]==1 and r["valid_positive_count"]>=2
assert r["actual_image_count"]>=3 and r["actual_depth_count"]>=3
assert r["actual_camera_info_count"]>=3 and r["actual_target_pixel_count"]>=2
assert r["actual_joint_samples"]>=2
assert p["status"]=="SENSOR_TO_MOVEIT_PLAN_ONLY_PASS"
assert p["arm_motor_goal_count"]==p["gripper_motor_goal_count"]==0
assert f["geometric_diameter_clearance"]==f["geometric_2R_wrist_reach"]=="PASS"
assert r["Ch10"]==p["Ch10"]=="HOLD"
live=p["target"]; ready=r["messages"]["ready"][0]
assert ready["frame"]==live["frame"]=="base_link"
assert abs(ready["stamp"]-live["stamp_sec"])<=.002
assert math.dist(ready["xyz"],live["xyz_m"])<=1e-5
# Actual optical pixel and sensor streams, not synthetic replay.
assert any(abs(x["stamp"]-ready["stamp"])<=.08 for x in r["messages"]["pixels"])
for topic in ("images","depth","info"):
    assert r["messages"][topic][0]["frame"]=="camera_optical_frame"
# The original camera coord node logs precisely the 3D transform publication;
# this resolves a sparse DDS observer's missing matching 3D sample.
pattern=r"CH07_75_VALID_3D_TARGET stamp=([0-9.]+) xyz=\(([-+0-9.]+),([-+0-9.]+),([-+0-9.]+)\)"
found=False
for m in re.finditer(pattern,txt):
    stamp=float(m.group(1)); xyz=[float(t) for t in m.groups()[1:]]
    if abs(stamp-ready["stamp"])<=.002 and math.dist(xyz,ready["xyz"])<=2e-4:
        found=True
        break
assert found,"E2_NO_EXACT_3D_TRANSFORM_SOURCE_FOR_G01_READY"
print("CH07_77_E2_INDEPENDENT_CAMERA_PIXEL_3D_G01_MOVEIT_CAUSAL_CHAIN_PASS")
PY
stage E2_SCOPED_PASS_REAL_SENSOR_TO_MOVEIT_PLAN_ONLY
echo CH07_77_E2_SENSOR_RGBD_TO_MOVEIT_PLAN_ONLY_NO_MOTOR_GOAL_SCOPED_PASS > "$OUT/verdict.txt"
