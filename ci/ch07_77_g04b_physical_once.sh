#!/usr/bin/env bash
# Ch07 #173 G04B: actual GazeboSimSystem physics, 2 fingers, true contact, lift and place.
# One NEW physical-contact boundary; G04A RGB-D and G03A/G03B motion retained as prior evidence, not rerun.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash;set -u
ROOT=/work;OUT="$ROOT/ci-results/ch07-77-g04b"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=81 ROS_LOCALHOST_ONLY=1 GZ_IP=127.0.0.1
export GZ_PARTITION="ch07_77_g04b_${GITHUB_RUN_ID:-local}_$$_$RANDOM"
export DEBIAN_FRONTEND=noninteractive
export CH07_77_G04B_RECEIPT="$OUT/g04b_physical_receipt.json"
export CH07_77_G04B_FIXTURE_RECEIPT="$OUT/g04b_fixture_receipt.json"
export CH07_77_G04B_NATIVE_RAW="$OUT/native_contacts.log"
export CH07_77_G04B_SUPPORT_RAW="$OUT/diag_support_contacts.log"
export CH07_77_G04B_SIMULATION_ONLY_VERIFIED=NO
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
 "scope":"G04B_GAZEBO_PHYSICAL_ROD_CONTACT_LIFT_PLACE",
 "status":"SCOPED_PASS" if int(rc)==0 else "FAIL",
 "rc":int(rc),"stage":stage,"shutdown":shutdown,
 "G02":"REPLAY_ACCEPTED_ARTIFACT_NOT_RERUN",
 "G04B_execution":"SCOPED_PASS_ONLY_AFTER_NATIVE_CONTACT_AUDIT","G04_grasp":"PASS_IF_RC0_ELSE_FAIL","Ch10":"HOLD"
},indent=2)+"\n")
PY
 echo "CH07_77_G04B_FINAL rc=$rc stage=$STAGE shutdown=$shutdown"
 exit "$rc"
}
trap cleanup EXIT
stage PREPARE_ORIGINAL_GAZEBO8_READONLY_ECS_HEADERS
# Build passive test-only observer in pinned disposable container.
# No robot, physics solver, effort, gravity, contact or FJT modifications.
if ! apt-cache show libgz-sim8-dev >/dev/null 2>&1;then
  timeout 15s curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
    -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
  codename="$(. /etc/os-release;printf '%s' "$VERSION_CODENAME")"
  test "$codename" = noble
  printf 'deb [arch=amd64 signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable %s main\n' "$codename" \
    > /etc/apt/sources.list.d/gazebo-stable.list
fi
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
  libgz-sim8-dev libgz-plugin2-dev cmake g++ pkg-config
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
# Test-only additional sensors: exactly the same original physical robot
# collision shapes, joint axes and controller. Diagnose finger2 blocking.
python3 "$ROOT/ci/ch07_77_g04b_instrument_finger_contacts.py" \
 "$OUT/robot.urdf" "$OUT/g04b_contact_sensors_receipt.json" \
 > "$OUT/instrumentation.log"
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
stage CREATE_NEW_TEST_ONLY_CONTACT_ENABLED_ROD_WORLD
python3 "$ROOT/ci/ch07_77_g04b_physics_fixture.py" \
  --source "$ROOT/ci/docker/fixtures/ch07_77_g02_dynamic_red_world.sdf" \
  --output "$OUT/g04b_contact_world.sdf" \
  --receipt "$OUT/g04b_fixture_receipt.json" >"$OUT/fixture.log"
stage BUILD_READ_ONLY_GAZEBO_DYNAMIC_ROD_ECS_WITNESS
timeout --signal=TERM --kill-after=5s 90s cmake \
 -S "$ROOT/ci/ch07_181_rod_trace" -B "$OUT/rod_ecs_build" \
 -DCMAKE_BUILD_TYPE=Release >"$OUT/rod_ecs_configure.log" 2>&1
timeout --signal=TERM --kill-after=5s 90s cmake \
 --build "$OUT/rod_ecs_build" --parallel 2 >"$OUT/rod_ecs_compile.log" 2>&1
test -s "$OUT/rod_ecs_build/libch07_181_rod_trace.so"
export GZ_SIM_SYSTEM_PLUGIN_PATH="$OUT/rod_ecs_build:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
export CH07_181_ROD_ECS_CSV="$OUT/gazebo_rod_real_static_gravity_velocity.csv"
export CH07_181_SYNC_CONTACT_CSV="$OUT/gazebo_rod_finger_contact_same_ecs_frame.csv"
export CH07_181_POSE_SOURCE_CSV="$OUT/gazebo_link_pose_component_provenance.csv"
python3 - "$OUT/g04b_contact_world.sdf" "$OUT/rod_ecs_scope.json" <<'PY'
import xml.etree.ElementTree as ET,json,sys
from pathlib import Path
file,receipt=map(Path,sys.argv[1:])
tree=ET.parse(file)
world=tree.getroot().find("./world[@name='book_camera']")
assert world is not None
rod=world.find("./model[@name='g04_grasp_cylinder']")
assert rod is not None and rod.findtext("static")=="false"
assert world.findtext("gravity").strip()=="0 0 -9.8"
assert rod.find("./link[@name='cylinder_link']/inertial/mass").text=="0.05"
ET.SubElement(world,"plugin",{
 "filename":"libch07_181_rod_trace.so",
 "name":"ch07_181::RodTrace"})
tree.write(file,encoding="unicode",xml_declaration=True)
receipt.write_text(json.dumps({"world_gravity":"0 0 -9.8",
"rod_static_original":False,"rod_mass_original_kg":.05,
"plugin":"READ_ONLY_GAZEBO_ROD_ECS_POSTUPDATE",
"observations":["Static","GravityEnabled","WorldPose","WorldLinearVelocity"],
"physics_mutated":False,"G00_G04A":"NOT_RERUN",
"G04B":"BLOCKED_PENDING_FULL_PHYSICS","G05":"NOT_RUN",
"Ch10":"HOLD"},indent=2)+"\n")
PY
stage START_ORIGINAL_REAL_GAZEBO_WITH_GAZEBO_SIM_SYSTEM
start rsp ros2 run robot_state_publisher robot_state_publisher \
 --ros-args --params-file "$OUT/rsp.yaml"
start gazebo gz sim -s -r -v 3 --headless-rendering "$OUT/g04b_contact_world.sdf"
READY=0
for attempt in $(seq 1 55);do
 if timeout 4s gz service -l 2>/dev/null |grep -Fq '/world/book_camera/create';then
 READY=1;break;fi
 sleep .3
done
[[ "$READY" -eq 1 ]] || { echo G04B_REAL_WORLD_NOT_READY;exit 3; }
stage REQUIRE_READ_ONLY_ROD_ECS_PLUGIN_INITIALIZED
# Plugin constructor creates the CSV header *before* any robot Goal.
# If the plugin is not loaded, stop here instead of wasting another
# full physical run and mislabeling missing evidence as a physics cause.
ldd "$OUT/rod_ecs_build/libch07_181_rod_trace.so" >"$OUT/rod_ecs_ldd.log" 2>&1
echo "CH07_181_ROD_ECS_EXPECTED_OUTPUT=$CH07_181_ROD_ECS_CSV" >>"$OUT/stages.log"
for attempt in $(seq 1 35);do
  [[ -s "$CH07_181_ROD_ECS_CSV" ]] && break
  sleep .2
done
if [[ ! -s "$CH07_181_ROD_ECS_CSV" ]];then
  echo CH07_181_ROD_ECS_PLUGIN_NOT_INITIALIZED
  grep -Ei 'CH07_181_ROD_ECS|trace|error|plugin' "$OUT/gazebo.log" |tail -50 || true
  exit 24
fi
head -1 "$CH07_181_ROD_ECS_CSV" >"$OUT/rod_ecs_startup_schema.txt"
# The constructor must create this read-only contact-synchrony stream
# before any arm or finger goal. ContactSensorData may still be absent;
# its absence is recorded and is NOT silently interpreted as zero force.
test -s "$CH07_181_SYNC_CONTACT_CSV" || {
  echo CH07_181_ECS_CONTACT_SYNC_STREAM_MISSING;exit 25;
}
head -1 "$CH07_181_SYNC_CONTACT_CSV" >"$OUT/rod_contact_sync_schema.txt"
echo CH07_181_ECS_CONTACT_SYNC_INITIALIZED >>"$OUT/stages.log"
test -s "$CH07_181_POSE_SOURCE_CSV" || {
 echo CH07_181_POSE_COMPONENT_SOURCE_MISSING;exit 26;
}
head -1 "$CH07_181_POSE_SOURCE_CSV" >"$OUT/rod_link_pose_provenance_schema.txt"
echo CH07_181_POSE_COMPONENT_PROVENANCE_INITIALIZED >>"$OUT/stages.log"
echo CH07_181_ROD_ECS_PLUGIN_INITIALIZED >>"$OUT/stages.log"
stage SPAWN_IDENTICAL_GAZEBO_URDF
timeout --signal=TERM --kill-after=5s 50s ros2 run ros_gz_sim create \
 -world book_camera -name my_robot -file "$OUT/robot.urdf" -z 0.0 >"$OUT/create.log" 2>&1
grep -q 'Entity creation successful' "$OUT/create.log"
# Issue #181 raw CI #43683958215: both Gazebo finger contact sensors
# continued to report ~13N even after actual rod moved >=0.15m away
# from measured physical collision centres. A contact topic alone cannot
# prove current grasp. Observe simultaneous native WORLD link/model poses
# using the EXISTING read-only SceneBroadcaster; do not touch physics.
POSE_TOPIC=/world/book_camera/dynamic_pose/info
pose_ready=0
for attempt in $(seq 1 20);do
  if timeout 4s gz topic -l |grep -Fxq "$POSE_TOPIC";then
    pose_ready=1;break;fi
  sleep .2
done
[[ "$pose_ready" == 1 ]] || { echo G04B_181_NATIVE_DYNAMIC_POSE_UNAVAILABLE;exit 23; }
echo "$POSE_TOPIC" >"$OUT/dynamic_pose_topic.txt"
timeout 8s gz topic -i -t "$POSE_TOPIC" >"$OUT/dynamic_pose_topic_info.log" 2>&1 || true
start dynamic_pose stdbuf -oL gz topic -e -t "$POSE_TOPIC"
echo G04B_181_READ_ONLY_GAZEBO_WORLD_POSE_WITNESS_START >> "$OUT/stages.log"
# The source-URDF FK used to admit the grasp point is relative to base_link.
# Prior G04B spawned the WORLD robot 50mm above that nominal origin but
# compared this BASE_LINK FK directly to WORLD rod/shelf pose. For the short
# 80mm rod the real finger collision volume then sat ABOVE the cylinder;
# raw sensor showed shelf-only 32975 contact events and zero finger contacts.
# Test-only world spawn now uses exactly base_link==world z=0; the original
# robot Xacro and both accepted G03/G04A upstream fixtures stay unchanged.
echo 'G04B_ROBOT_BASE_WORLD_SPAWN_Z_M=0.0' > "$OUT/base_world_alignment.txt"
timeout 10s gz model --model my_robot --link link_wrist --pose \
 >"$OUT/gz_wrist_native_preflight.log" 2>&1 || true
stage VERIFY_ACTUAL_DYNAMICAL_ROD_AND_NATIVE_CONTACT_TOPIC
timeout 12s gz model --list >"$OUT/gz_models.txt" 2>&1
grep -q g04_grasp_cylinder "$OUT/gz_models.txt"
timeout 12s gz model --model g04_grasp_cylinder --pose >"$OUT/gz_rod_initial.txt" 2>&1
CONTACT_TOPIC=/world/book_camera/model/g04_grasp_cylinder/link/cylinder_link/sensor/book_ch07_77_rod_contact/contact
echo "$CONTACT_TOPIC" > "$OUT/contact_native_topic.txt"
CONTACT_READY=0
for attempt in $(seq 1 40);do
  if timeout 5s gz topic -l | grep -Fxq "$CONTACT_TOPIC";then
    CONTACT_READY=1;break
  fi
  sleep .2
done
[[ "$CONTACT_READY" -eq 1 ]] || { echo G04B_NATIVE_CONTACT_SENSOR_TOPIC_NOT_AVAILABLE;exit 9; }
timeout 6s gz topic -i -t "$CONTACT_TOPIC" >"$OUT/contact_topic_info.txt" 2>&1 || true
start native_contacts stdbuf -oL gz topic -e -t "$CONTACT_TOPIC"
# Record independent finger and pedestal collision partners. This does
# not modify contact physics: all are passive native Gazebo sensors.
# All failures retain logs and keep G04B FAIL, never infer success from
# the presence/absence of this diagnostic signal alone.
DIAG_NAMES=(finger1 finger2 support)
DIAG_TOPICS=(
 '/world/book_camera/model/my_robot/link/finger1/sensor/g04b_finger1_contacts/contact'
 '/world/book_camera/model/my_robot/link/finger2/sensor/g04b_finger2_contacts/contact'
 '/world/book_camera/model/g04_support/link/shelf_link/sensor/g04b_support_contacts/contact'
)
for idx in "${!DIAG_NAMES[@]}";do
  name="${DIAG_NAMES[$idx]}"
  topic="${DIAG_TOPICS[$idx]}"
  echo "$topic" > "$OUT/diag_${name}_topic.txt"
  ready=0
  for attempt in $(seq 1 30);do
    if timeout 5s gz topic -l | grep -Fxq "$topic";then
      ready=1;break
    fi
    sleep .2
  done
  if [[ "$ready" == 1 ]];then
    start "diag_${name}_contacts" stdbuf -oL gz topic -e -t "$topic"
    echo "G04B_DIAGNOSTIC_SENSOR_READY_${name}" >>"$OUT/stages.log"
  else
    echo "G04B_DIAGNOSTIC_SENSOR_UNAVAILABLE_${name}" >>"$OUT/stages.log"
  fi
done
# Gazebo actual pose and contact data are independent ground truth.
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
# ros2cli type auto-discovery can race a newly active broadcaster.
# This optional CLI snapshot is NOT the admission gate: the new typed
# rclpy witness requires >=3 real joint_states before it sends any Goal.
timeout 15s ros2 topic echo /joint_states sensor_msgs/msg/JointState --once \
 >"$OUT/joints_before.log" 2>&1 || \
 echo 'CH07_77_G04B_CLI_JOINT_ECHO_OPTIONAL; TYPED_WITNESS_IS_AUTHORITATIVE' \
 >>"$OUT/joints_before.log"
stage START_REAL_MOVEIT_MOVE_GROUP_FROM_IDENTICAL_GAZEBO_DESCRIPTION
start move_group ros2 run moveit_ros_move_group move_group \
 --ros-args --params-file "$OUT/move_group.yaml"
stage NEW_G04B_ACTUAL_SIMULATED_ARM_AND_GRIPPER_PHYSICAL_CONTACT
export CH07_77_G04B_SIMULATION_ONLY_VERIFIED=YES
timeout --signal=TERM --kill-after=12s 440s \
 python3 "$ROOT/ci/ch07_77_g04b_actual_physics_witness.py" \
 >"$OUT/g04b_witness.log" 2>&1
grep -q CH07_77_G04B_GAZEBO_OBJECT_LIFT_HOLD_PLACE_GEOMETRY_CANDIDATE_PASS_CONTACT_AUDIT_REQUIRED "$OUT/g04b_witness.log"
stage INDEPENDENT_GAZEBO_NATIVE_TWO_FINGER_CONTACT_AUDIT
# End native recorder cleanly before parsing; Gazebo continues until cleanup.
contact_index=-1
for ((i=0;i<${#NAMES[@]};i++));do
  if [[ "${NAMES[$i]}" == native_contacts ]];then
    contact_index="$i";break
  fi
done
[[ "$contact_index" -ge 0 ]] || { echo G04B_NATIVE_RECORDER_NOT_OWNED;exit 8; }
kill -TERM -- "-${OWNED[$contact_index]}" 2>/dev/null || true
wait "${OWNED[$contact_index]}" 2>/dev/null || true
# Independent parser is always strict; geometry-only success is insufficient.
python3 "$ROOT/ci/ch07_77_g04b_verify_contacts.py" \
 "$OUT/native_contacts.log" "$OUT/g04b_physical_receipt.json" \
 "$OUT/g04b_contact_audit.json" "$OUT/diag_support_contacts.log" \
 > "$OUT/g04b_contact_audit.log" 2>&1
grep -q CH07_77_G04B_ACTUAL_BILATERAL_ROD_CONTACT_AND_WORLD_POSE_PASS "$OUT/g04b_contact_audit.log"
stage G04B_REAL_GAZEBO_BILATERAL_CONTACT_LIFT_AND_PLACE_SCOPED_PASS
echo CH07_77_G04B_DYNAMIC_ROD_ACTUAL_CONTACT_LIFT_PLACE_SCOPED_PASS > "$OUT/verdict.txt"
