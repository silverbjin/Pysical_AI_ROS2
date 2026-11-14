#!/usr/bin/env bash
# Ch07 #173 G04B: actual GazeboSimSystem physics, 2 fingers, true contact, lift and place.
# One NEW physical-contact boundary; G04A RGB-D and G03A/G03B motion retained as prior evidence, not rerun.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash;set -u
ROOT=/work;OUT="$ROOT/ci-results/ch07-181-free-space"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=81 ROS_LOCALHOST_ONLY=1 GZ_IP=127.0.0.1
export GZ_PARTITION="ch07_77_g04b_${GITHUB_RUN_ID:-local}_$$_$RANDOM"
export DEBIAN_FRONTEND=noninteractive
export CH07_181_RECEIPT="$OUT/g04b_physical_receipt.json"
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
 "scope":"ISSUE_181_FREE_SPACE_ACTUATION_ONLY",
 "status":"FREE_SPACE_ACTUATION_SCOPED_PASS" if int(rc)==0 else "FAIL",
 "rc":int(rc),"stage":stage,"shutdown":shutdown,
 "G02":"REPLAY_ACCEPTED_ARTIFACT_NOT_RERUN",
 "G04B_execution":"NOT_RUN","G04_grasp":"NOT_RUN","Ch10":"HOLD"
},indent=2)+"\n")
PY
 echo "CH07_77_G04B_FINAL rc=$rc stage=$STAGE shutdown=$shutdown"
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
# Test-only additional sensors: exactly the same original physical robot
# collision shapes, joint axes and controller. Diagnose finger2 blocking.
python3 "$ROOT/ci/ch07_77_g04b_instrument_finger_contacts.py" \
 "$OUT/robot.urdf" "$OUT/g04b_contact_sensors_receipt.json" \
 > "$OUT/instrumentation.log"
check_urdf "$OUT/robot.urdf" >"$OUT/check_urdf.log"
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

stage REMOVE_ROD_SUPPORT_BIN_FROM_GENERATED_TEST_ONLY_WORLD
python3 - "$OUT/g04b_contact_world.sdf" "$OUT/free_world.sdf" "$OUT/empty_world_contract.json" <<'PY'
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
p,o,r=map(Path,sys.argv[1:])
tree=ET.parse(p)
world=tree.getroot().find("./world[@name='book_camera']")
assert world is not None
names=[m.get("name") for m in world.findall("model")]
expected={"ground","g04_support","g04_grasp_cylinder","g04_bin_support"}
assert set(names)==expected,names
for m in list(world.findall("model")):
 if m.get("name")!="ground":world.remove(m)
assert [m.get("name") for m in world.findall("model")]==["ground"]
assert world.find("./plugin[@filename='gz-sim-contact-system']") is not None
tree.write(o,encoding="unicode",xml_declaration=True)
r.write_text(json.dumps({"original_fixture_models":names,"remaining_models":["ground"],
"rod":False,"pedestal":False,"bin":False,"force_attach":False,
"G00_G04A":"NOT_RERUN","Ch10":"HOLD"},indent=2)+"\n")
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
stage SPAWN_IDENTICAL_GAZEBO_URDF
timeout --signal=TERM --kill-after=5s 50s ros2 run ros_gz_sim create \
 -world book_camera -name my_robot -file "$OUT/robot.urdf" -z 0.0 >"$OUT/create.log" 2>&1
grep -q 'Entity creation successful' "$OUT/create.log"
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

stage CHECK_UNMODIFIED_G04B_TEST_ONLY_ROD_SUPPORT_BEFORE_APPROACH
timeout 12s gz model --list > "$OUT/gz_models.txt" 2>&1
grep -q my_robot "$OUT/gz_models.txt"
for expected_model in g04_grasp_cylinder g04_support g04_bin_support;do
 grep -q "$expected_model" "$OUT/gz_models.txt"
done
timeout 12s gz model --model g04_grasp_cylinder --pose >"$OUT/rod_before_pregrasp.txt" 2>&1
cat > "$OUT/physical_world_comparison_contract.json" <<'JSON'
{"comparison":"same real robot and arm FJT q4=pi/2 and 3 isolated finger FJT goals",
 "changed_factor":"GENERATED_GAZEBO_WORLD_ONLY",
 "old_world":"ground_only_CI_43580533046",
 "new_world":"original_unmodified_G04B_test_only_rod_support_bin",
 "rod_or_support_approach":false,"G00_G04A":"NOT_RERUN",
 "G04B_PHYSICAL_GRASP":"NOT_RUN","G05":"NOT_RUN","Ch10":"HOLD"}
JSON
for finger in finger1 finger2;do
 topic="/world/book_camera/model/my_robot/link/$finger/sensor/g04b_$finger""_contacts/contact"
 echo "$topic" > "$OUT/native_$finger.topic"
 ready=0
 for attempt in $(seq 1 30);do
  if timeout 5s gz topic -l | grep -Fxq "$topic";then ready=1;break;fi
  sleep .2
 done
 [[ "$ready" -eq 1 ]]||{ echo "G04B_181_NATIVE_CONTACT_SENSOR_MISSING_$finger";exit 9; }
 start "native_$finger" stdbuf -oL gz topic -e -t "$topic"
done

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

timeout 12s ros2 control list_hardware_interfaces -c /controller_manager >"$OUT/hardware_interfaces.log"
for finger in joint_finger1 joint_finger2;do
 grep -Eq "$finger/position.*claimed" "$OUT/hardware_interfaces.log"
done

stage ONE_G04B_INITIAL_PREOPEN_BEFORE_DIRECT_ARM_FJT_COMPARISON_NO_APPROACH
export CH07_181_GAZEBO_ONLY=YES
export CH07_181_COMMAND_SEQUENCE=ISOLATED
export CH07_181_PREOPEN=YES
timeout --signal=TERM --kill-after=10s 95s \
 python3 "$ROOT/ci/ch07_181_free_space_witness.py" >"$OUT/witness.log" 2>&1
grep -q CH07_181_FREE_SPACE_ISOLATED_SEQUENCE_SCOPED_PASS_NO_GRASP "$OUT/witness.log"
timeout 12s gz model --model g04_grasp_cylinder --pose >"$OUT/rod_after_pregrasp.txt" 2>&1
python3 - "$OUT/rod_before_pregrasp.txt" "$OUT/rod_after_pregrasp.txt" "$OUT/rod_static_motion_audit.json" <<'PY'
import math,json,re,sys
from pathlib import Path
pat=re.compile(r"Pose \[ XYZ \(m\) \] \[ RPY \(rad\) \]:\s*\n\s*\[\s*([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s*\]")
def xyz(p):
 s=Path(p).read_text()
 m=pat.search(s)
 if m is None:raise RuntimeError("G04B_181_ROD_POSE_UNPARSEABLE")
 return tuple(float(v) for v in m.groups())
before,after=xyz(sys.argv[1]),xyz(sys.argv[2])
delta=math.dist(before,after)
Path(sys.argv[3]).write_text(json.dumps({"before":before,"after":after,"displacement_m":delta,
 "no_contact_motion_pass":delta<=.008},indent=2)+"\n")
if delta>.008:raise RuntimeError("G04B_181_ROD_DISTURBED_DURING_PREGRASP")
PY
stage VERIFY_NO_NATIVE_FINGER_CONTACT
for finger in finger1 finger2;do
 if grep -q 'collision1:' "$OUT/native_$finger.log";then
  echo "G04B_181_UNEXPECTED_FINGER_CONTACT_$finger"
  exit 7
 fi
done
stage ISSUE_181_PHYSICAL_WORLD_PREGRASP_ACTUATION_ONLY_NOT_GRASP
echo CH07_181_PHYSICAL_WORLD_PREGRASP_SCOPED_PASS_NO_G04B_NO_G05 > "$OUT/verdict.txt"
