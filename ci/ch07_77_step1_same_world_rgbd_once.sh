#!/usr/bin/env bash
# Issue #173 Step1: G04B proven physical short-rod fixture in G04A REAL OGRE2 RGB-D pipeline.
# NO MoveIt motion, no arm/gripper FJT Goal, no native object modification.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch07-step1-short-live"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=82 GZ_IP=127.0.0.1
export GZ_PARTITION="book_ch07_77_step1_short_${GITHUB_RUN_ID:-local}_$_$RANDOM"
export QT_QPA_PLATFORM=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
export ROS_LOCALHOST_ONLY=1 DEBIAN_FRONTEND=noninteractive
export CH07_77_G04A_RECEIPT="$OUT/g04a_live_receipt.json"
export CH07_77_G04B_SHORT_LIVE=YES
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
 "scope":"STEP1_G04B_80MM_SAME_PHYSICAL_WORLD_REAL_RGBD_G01_NO_MOTOR_GOAL",
 "status":"SCOPED_PASS" if int(rc)==0 else "FAIL",
 "stage":stage,"rc":int(rc),"shutdown":shutdown,
 "G03":"NOT_RUN","G04":"NOT_RUN","Ch10":"HOLD"},indent=2)+"\n")
PY
  echo "CH07_77_STEP1_SHORT_LIVE_FINAL rc=$result stage=$STAGE shutdown=$shutdown"
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
  ros-jazzy-moveit-ros-move-group ros-jazzy-moveit-msgs
  libgz-sim8-dev)  # Reused exact G04B dependency to provide DART 6.13.2
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
stage GENERATE_PROVEN_G04B_SHORT_80MM_PHYSICAL_WORLD
python3 "$ROOT/ci/ch07_77_g04b_physics_fixture.py" \
 --source "$ROOT/ci/docker/fixtures/ch07_77_g02_dynamic_red_world.sdf" \
 --output "$OUT/graspable_dynamic_world.sdf" \
 --receipt "$OUT/fixture_receipt.json" > "$OUT/fixture.log"
stage APPLY_PROVEN_C12_TEST_ONLY_SOLID_BIN_ORIENTATION
python3 "$ROOT/ci/ch07_181_bin_yaw_single_factor.py" \
 --world "$OUT/graspable_dynamic_world.sdf" \
 --receipt "$OUT/bin_yaw_receipt.json" > "$OUT/bin_yaw.log"
stage SAME_PHYSICAL_PR202_WORLD_FIXED_BASE_ROBOT
timeout 35s gz sdf -p "$OUT/robot.urdf" > "$OUT/robot_source.sdf"
python3 "$ROOT/ci/ch07_181_fixed_world_base_anchor.py" \
 --input "$OUT/robot_source.sdf" \
 --output "$OUT/robot_anchored.sdf" \
 --receipt "$OUT/base_anchor_receipt.json" > "$OUT/base_anchor.log"
# Match G04B DART 6.13.2 source-only lower limit margin. It is not a Goal.
DART_VERSION="$(dpkg-query -W -f='${Version}' 'libdart-core+collisions+odelcpsolver6.13')"
case "$DART_VERSION" in 6.13.2*) ;; *) echo "UNKNOWN_DART_VERSION=$DART_VERSION";exit 30;; esac
python3 "$ROOT/ci/ch07_181_g04b_dart_limit_margin.py" \
 --input "$OUT/robot_anchored.sdf" \
 --output "$OUT/robot_physical.sdf" \
 --receipt "$OUT/dart_margin_receipt.json" > "$OUT/dart_margin.log"
timeout 20s gz sdf -k "$OUT/robot_physical.sdf" > "$OUT/sdf_validate.log" 2>&1
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
stage SPAWN_SAME_PHYSICAL_ROBOT_ANCHORED_WORLD_Z0_WITH_RGBD
timeout --signal=TERM --kill-after=5s 48s ros2 run ros_gz_sim create \
 -world book_camera -name my_robot -file "$OUT/robot_physical.sdf" -z 0.0 \
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
stage START_SAFE_ADMISSION_BEFORE_ANY_DETECTOR_3D_INPUT
start admission ros2 run vision_basics mission_controller --ros-args -p use_sim_time:=true
stage START_INDEPENDENT_WITNESS_BEFORE_ONE_SHOT_PUBLICATION
start witness python3 "$ROOT/ci/ch07_77_g04a_live_small_target_witness.py"
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
# Owned: rsp=0,gazebo=1,bridge=2,admission=3,witness=4,detector=5,coord=6.
WITNESS_PID="${OWNED[4]}"
# DDS can deliver G01 ready before the read-only G04A witness receives the
# matching 3D message. Preserve that standalone witness failure unmodified.
WITNESS_RC=0
wait "$WITNESS_PID" || WITNESS_RC="$?"
if [[ "$WITNESS_RC" -ne 0 ]];then
  grep -q 'MISSION_TARGET_NOT_FROM_SENSOR' "$OUT/witness.log" || {
    echo CH07_E2_UNRELATED_SENSOR_WITNESS_FAILURE;exit "$WITNESS_RC";
  }
  echo 'STEP1_PRIOR_WITNESS_SPARSE_3D_DDS_RACE_INDEPENDENT_STAMP_AUDIT_REQUIRED' >>"$OUT/stages.log"
else
  grep -q CH07_77_G04B_SHORT_SAME_WORLD_REAL_RGBD_G01_NO_GOAL_SCOPED_PASS "$OUT/witness.log"
fi
stage REVIEW_REAL_NATIVE_OBJECT_EXISTS_AND_NO_MOTION
# Harmonic 'gz model -l' means LINK, not list; --list queries real Gazebo.
# A live world can finish its finite iterations before the ROS witness ends.
# Thus this evidence must be captured immediately after spawn, not now.
grep -q 'g04_grasp_cylinder' "$OUT/gz_models.txt" || {
  echo "CH07_77_G04A_GZ_MODEL_LIST_MISSING_RED_CYLINDER"; exit 7;
}
python3 - "$OUT/g04a_live_receipt.json" "$OUT/fixture_receipt.json" "$OUT/bin_yaw_receipt.json" "$OUT/base_anchor_receipt.json" "$OUT/coord.log" "$OUT/gz_red_pose.txt" <<'PY'
import json,math,re,sys
from pathlib import Path
paths=[Path(p) for p in sys.argv[1:]]
r,f,bin_yaw,anchor=[json.loads(p.read_text()) for p in paths[:4]]
coord=paths[4].read_text()
assert r["status"]=="SCOPED_PASS" and r.get("same_physical_80mm_world") is True, r
assert f["rod_static"] is False and f["radius_m"]==.012 and f["height_m"]==.08
assert f["rod_center_initial_world_m"]==[.70,0,1.94] and f["world_spawn_robot_base_z_m"]==0.
assert bin_yaw["bin_world_center_m"]==[.55,.25,1.63]
assert bin_yaw["only_change"]=="real_bin_model_yaw_0_to_0.35_rad"
assert anchor["anchor"]["parent"]=="world" and anchor["anchor"]["child"]=="base_link"
assert r["actual_ready_count"]==1 and r["valid_positive_count"]>=2
assert min(r["actual_image_count"],r["actual_depth_count"],r["actual_camera_info_count"])>=3
assert min(r["actual_target_pixel_count"],r["actual_3d_target_count"])>=2
assert r["actual_joint_samples"]>=2
assert all(x["frame"]=="camera_optical_frame" for k in ("images","depth","info","pixels") for x in r["messages"][k][:2])
ready=r["messages"]["ready"][0]
assert ready["frame"]=="base_link"
assert .665<=ready["xyz"][0]<=.71 and abs(ready["xyz"][1])<=.09
assert 1.80<=ready["xyz"][2]<=2.08
assert any(abs(x["stamp"]-ready["stamp"])<=.08 for x in r["messages"]["pixels"])
# Verify original 3D source publication from real camera/Depth/K/TF.
pat=r"CH07_75_VALID_3D_TARGET stamp=([0-9.]+) xyz=\(([-+0-9.]+),([-+0-9.]+),([-+0-9.]+)\)"
assert any(abs(float(m.group(1))-ready["stamp"])<=.002
               and math.dist([float(x) for x in m.groups()[1:]],ready["xyz"])<=2e-4
               for m in re.finditer(pat,coord)),"NO_EXACT_SENSOR_SOURCE_FOR_SHORT_PHYSICAL_WORLD"
assert "g04_grasp_cylinder" in paths[5].read_text() or paths[5].stat().st_size>20
out={"scope":"STEP1_G04B_SHORT_ROD_SAME_WORLD_CAMERA_G01",
     "status":"SCOPED_PASS_NO_GOALS","robot_world_anchor":True,
     "fixture_radius_m":f["radius_m"],"fixture_height_m":f["height_m"],
     "fixture_world_xyz_m":f["rod_center_initial_world_m"],
     "actual_base_link_rgbd_target":ready,
     "arm_motor_goals":0,"gripper_motor_goals":0,
     "release_clearance":"NOT_VERIFIED","G04B":"BLOCKED",
     "E2E":"BLOCKED","Ch10":"HOLD"}
(paths[0].parent/"same_world_rgbd_receipt.json").write_text(
    json.dumps(out,indent=2,allow_nan=False)+"\\n")
print("CH07_STEP1_G04B_SHORT_ROD_REAL_OGRE2_RGBD_G01_SCOPED_PASS_NO_GOALS")
PY
stage STEP1_SAME_WORLD_RGBD_SCOPED_PASS_NO_GOALS
echo CH07_STEP1_SAME_PHYSICAL_WORLD_RGBD_G01_NO_MOTOR_GOAL_SCOPED_PASS > "$OUT/verdict.txt"
