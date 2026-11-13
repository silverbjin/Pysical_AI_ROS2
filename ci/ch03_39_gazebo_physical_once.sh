#!/usr/bin/env bash
# Ch03 §3.9 physical teleop: CH03's actual ROS->GZ joint2 path and real Gazebo physics.
# The Ch03 original executable joint_position_cli is absent; don't invent it.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work;OUT="$ROOT/ci-results/ch03-39-physical";mkdir -p "$OUT"
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
 echo "CH03_39_PHYS_SIGKILL_ESCALATED_PGID=$pid" >> "$OUT/stages.log"
 return 1
}
cleanup(){
 local rc="$?";trap - EXIT;set +e
 local idx shutdown=SIGTERM_OWNED_GROUPS
 for ((idx=${#OWNED[@]}-1;idx>=0;idx--)); do
   stop_group "${OWNED[$idx]}" || shutdown=SIGKILL_ESCALATION
 done
 if [[ "$shutdown" == SIGKILL_ESCALATION && "$rc" == 0 ]]; then rc=75; fi
 printf '{"chapter":"Ch03","section":"3.9","exit_code":%d,"stage":"%s","shutdown":"%s","status":"%s","original_ch03_teleop":"EXISTING_ORIGINAL_EXECUTABLE","ch10":"HOLD"}\n' \
 "$rc" "$STAGE" "$shutdown" "$([[ "$rc" == 0 ]] && echo SCOPED_PASS || echo FAIL)" > "$OUT/result.json"
 echo "CH03_39_PHYS_SHUTDOWN=$shutdown rc=$rc" | tee -a "$OUT/stages.log"
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
# check_urdf prints a LINK tree, not joint names. Inspect the parsed
# model itself instead of grep'ing the human-readable tree output.
python3 - "$OUT/robot.urdf" <<'PY'
import sys,xml.etree.ElementTree as ET
root=ET.parse(sys.argv[1]).getroot()
joints={x.attrib["name"]:x for x in root.findall("joint")}
assert {"joint1","joint2"}.issubset(joints)
assert joints["joint2"].attrib["type"]=="revolute"
plugins=root.findall(".//gazebo/plugin")
control=[p for p in plugins
         if p.attrib.get("filename")=="gz-sim-joint-position-controller-system"
         and p.findtext("joint_name")=="joint2"]
assert len(control)==1
assert control[0].findtext("topic")=="/model/my_robot/joint2/cmd_pos"
state=[p for p in plugins if p.attrib.get("filename")==
       "gz-sim-joint-state-publisher-system"]
assert len(state)==1 and "joint2" in [x.text for x in state[0].findall("joint_name")]
print("CH03_39_PHYS_GENERATED_URDF_JOINT2_PLUGIN_CONTRACT_PASS")
PY
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
[[ "$READY" == 1 ]] || { echo CH03_39_PHYS_GAZEBO_WORLD_NOT_READY;exit 3; }
stage ORIGINAL_ROS_GAZEBO_BRIDGE
start bridge ros2 run ros_gz_bridge parameter_bridge \
 --ros-args -p config_file:="$WS/src/my_robot_description/config/ros_gz_bridge.yaml"
stage SPAWN_REAL_CH03_MODEL_WITH_ORIGINAL_NAME
timeout --signal=TERM --kill-after=5s 40s \
 ros2 run ros_gz_sim create -world my_first_world \
 -name my_robot -file "$OUT/robot.urdf" -z 0.1 \
 2>&1 | tee "$OUT/spawn.log"
grep -q 'Entity creation successful' "$OUT/spawn.log"
stage WAIT_REAL_ROS_GAZEBO_BRIDGE_READY
# The bridge starts asynchronously after spawn: first topic-info call can
# legitimately return code 1 before its DDS subscription is registered.
BRIDGE_READY=0
for attempt in $(seq 1 30); do
  if timeout 4s ros2 topic info -v /joint1/cmd_pos > "$OUT/command_joint1_topic.txt" 2>&1 &&
     grep -Eq 'Subscription count: [1-9]' "$OUT/command_joint1_topic.txt" &&
     timeout 4s ros2 topic info -v /joint2/cmd_pos > "$OUT/command_joint2_topic.txt" 2>&1 &&
     grep -Eq 'Subscription count: [1-9]' "$OUT/command_joint2_topic.txt"; then
    BRIDGE_READY=1; break
  fi
  sleep .25
done
[[ "$BRIDGE_READY" == 1 ]] || {
  echo CH03_39_PHYS_TWO_JOINT_BRIDGES_NOT_READY >&2; cat "$OUT/bridge.log"; exit 4;
}
stage WAIT_REAL_GAZEBO_JOINT_STATES_AND_CLOCK
STATE_READY=0
for attempt in $(seq 1 25); do
  if timeout 4s ros2 topic info -v /joint_states > "$OUT/state_topic.txt" 2>&1 &&
      grep -Eq 'Publisher count: [1-9]' "$OUT/state_topic.txt"; then
    STATE_READY=1; break
  fi
  sleep .25
done
[[ "$STATE_READY" == 1 ]] || {
  echo CH03_39_PHYS_JOINT_STATES_BRIDGE_NOT_READY >&2;cat "$OUT/bridge.log";exit 5;
}
timeout 18s ros2 topic echo /clock --once > "$OUT/clock.txt" 2>&1
grep -q 'sec:' "$OUT/clock.txt"
stage ORIGINAL_CH03_INTERACTIVE_TTY_TO_BOTH_PHYSICAL_JOINTS
# Reuse only the already-proven Gazebo launch prerequisites.
# Drive the original keyboard teleop through PTY; independent observer
# measures actual Gazebo /joint_states, not simulated ROS JointState fakes.
export CH03_39_PHYS_OUT="$OUT"
timeout --signal=TERM --kill-after=5s 45s \
 python3 "$ROOT/ci/ch03_39_gazebo_physical_probe.py" \
 2>&1 | tee "$OUT/physical_probe.log"
grep -q CH03_39_ACTUAL_INTERACTIVE_GAZEBO_FEEDBACK_SCOPED_PASS \
 "$OUT/physical_probe.log"
stage CH03_39_PHYSICAL_TELEOP_SCOPED_PASS
echo CH03_39_PTY_BOTH_PHYSICAL_GAZEBO_JOINTS_PASS_GUI_NOT_RUN \
 | tee "$OUT/verdict.txt"
