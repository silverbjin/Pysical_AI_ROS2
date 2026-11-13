#!/usr/bin/env bash
# Ch09 #165: ONLY missing direct foot-ground contact measurement.
# Original Ch09 model, stand_up.py, joints/PID/world physics untouched.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch09-165-contact"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=95 ROS_LOCALHOST_ONLY=1
export GZ_PARTITION="book_ch09_contact_$GITHUB_RUN_ID-$RANDOM-$$" GZ_IP=127.0.0.1
export QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1
printf 'source_sha=%s\nGZ_PARTITION=%s\n' "${RUN_SOURCE_SHA:-UNKNOWN}" "$GZ_PARTITION" > "$OUT/environment.txt"
STAGE=INIT
OWNED=()
OWNED_NAMES=()
stage(){ STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
start(){
  local name="$1"; shift
  setsid "$@" > "$OUT/$name.log" 2>&1 &
  OWNED+=("$!")
  OWNED_NAMES+=("$name")
  echo "START:$name:pgid=$!" | tee -a "$OUT/stages.log"
}
group_alive(){
  local pgid="$1"
  ps -eo pgid=,stat= | awk -v g="$pgid" '$1==g && $2 !~ /^Z/ {a=1} END {exit !a}'
}
stop_group(){
  local pgid="$1" name="$2" attempt
  if ! group_alive "$pgid"; then wait "$pgid" 2>/dev/null || true; return 0; fi
  kill -INT -- "-$pgid" 2>/dev/null || true
  for attempt in $(seq 1 25); do
    if ! group_alive "$pgid"; then
      wait "$pgid" 2>/dev/null || true
      echo "EXIT_SIGINT:$name" >> "$OUT/stages.log"
      return 0
    fi
    sleep .2
  done
  kill -TERM -- "-$pgid" 2>/dev/null || true
  for attempt in $(seq 1 25); do
    if ! group_alive "$pgid"; then
      wait "$pgid" 2>/dev/null || true
      echo "EXIT_SIGTERM:$name" >> "$OUT/stages.log"
      return 0
    fi
    sleep .2
  done
  kill -KILL -- "-$pgid" 2>/dev/null || true
  wait "$pgid" 2>/dev/null || true
  echo "EXIT_SIGKILL:$name" >> "$OUT/stages.log"
  return 1
}
cleanup(){
  local rc="$?" idx final="$rc" status=OWNED_GROUPS_EXITED_NO_SIGKILL
  trap - EXIT
  set +e
  for ((idx=${#OWNED[@]}-1;idx>=0;idx--)); do
    stop_group "${OWNED[$idx]}" "${OWNED_NAMES[$idx]}" || status=SIGKILL_ESCALATION
  done
  if [[ "$status" == SIGKILL_ESCALATION && "$final" -eq 0 ]]; then final=75; fi
  python3 - "$OUT/result.json" "$STAGE" "$final" "$status" <<'PYRESULT'
import json,sys
from pathlib import Path
path,stage,rc,shutdown=sys.argv[1:]
data={"chapter":"Ch09","section":"9.8","scope":"GROUND_SENSOR_FOUR_ORIGINAL_FEET_TEST_ONLY_WORLD",
      "status":"PASS" if int(rc)==0 else "FAIL","last_stage":stage,"exit_code":int(rc),
      "shutdown":shutdown,"source_model_changed":False,"stand_up_changed":False,
      "friction_coefficient_measured":False,"ch10":"HOLD"}
Path(path).write_text(json.dumps(data,indent=2)+"\n")
PYRESULT
  echo "CH09_165_FINAL stage=$STAGE rc=$final shutdown=$status" | tee -a "$OUT/stages.log"
  exit "$final"
}
trap cleanup EXIT

WS="$ROOT/Ch09/ros2_ws"
stage BUILD_ORIGINAL_CH09_PACKAGE
cd "$WS"
timeout --signal=TERM --kill-after=8s 135s colcon build --symlink-install \
  --packages-up-to my_quadruped_bot > "$OUT/colcon.log" 2>&1
set +u; source install/setup.bash; set -u
ros2 pkg prefix my_quadruped_bot > "$OUT/ros_package_prefix.txt"

stage ORIGINAL_XACRO_AND_TEST_ONLY_WORLD
xacro "$WS/src/my_quadruped_bot/urdf/robot.urdf.xacro" > "$OUT/robot.urdf"
check_urdf "$OUT/robot.urdf" > "$OUT/urdf_check.txt"
python3 "$ROOT/ci/docker/ch09_165_instrument_ground_contacts.py" \
  "$WS/src/my_quadruped_bot/worlds/empty_world.sdf" \
  "$OUT/contact_world.sdf" "$OUT/world_fixture_manifest.json"
python3 - "$OUT/robot.urdf" "$OUT/original_foot_contract.json" <<'PYFOOT'
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
root=ET.parse(sys.argv[1]).getroot()
feet=["fr_foot","fl_foot","rr_foot","rl_foot"]
info={}
for name in feet:
    link=root.find(f"./link[@name='{name}']")
    assert link is not None and len(link.findall("./collision"))==1
    gizmos=[g for g in root.findall("./gazebo") if g.get("reference")==name]
    assert gizmos
    info[name]={"collision_count":1,
        "source_gazebo_mu1":gizmos[0].find("mu1").get("value") if gizmos[0].find("mu1") is not None else None,
        "source_gazebo_mu2":gizmos[0].find("mu2").get("value") if gizmos[0].find("mu2") is not None else None}
Path(sys.argv[2]).write_text(json.dumps(info,indent=2)+"\n")
assert all(info[f]["source_gazebo_mu1"]=="1.0" and info[f]["source_gazebo_mu2"]=="1.0" for f in feet)
print("CH09_165_FOUR_ORIGINAL_FOOT_COLLISION_AND_MU_TAGS_FOUND")
PYFOOT

stage REAL_GAZEBO_CONTACT_SYSTEM
start gazeboserver gz sim -s -r -v 3 --iterations 35000 "$OUT/contact_world.sdf"
WORLD_READY=0
for attempt in $(seq 1 35); do
  if timeout 4s gz service -l 2>/dev/null | grep -Fq /world/my_empty_world/create; then WORLD_READY=1; break; fi
  sleep .35
done
[[ "$WORLD_READY" == 1 ]] || { echo "CH09_165_WORLD_NOT_READY"; exit 61; }

stage ORIGINAL_ROBOT_SPAWN
timeout --signal=TERM --kill-after=6s 50s \
  ros2 run ros_gz_sim create -world my_empty_world -name my_quadruped \
  -file "$OUT/robot.urdf" -z .5 2>&1 | tee "$OUT/spawn.log"
grep -q 'Entity creation successful' "$OUT/spawn.log"

stage ORIGINAL_JOINT_BRIDGE_AND_CONTACT_TOPIC
start original_joint_bridge ros2 run ros_gz_bridge parameter_bridge \
  --ros-args -p config_file:="$WS/src/my_quadruped_bot/config/ros_gz_bridge.yaml"
timeout 15s ros2 topic echo /joint_states --once > "$OUT/joint_ready.txt"
CONTACT_READY=0
for attempt in $(seq 1 35); do
  if timeout 4s gz topic -l | grep -Fxq /book_ch09/ground_contacts; then CONTACT_READY=1; break; fi
  sleep .3
done
timeout 5s gz topic -i -t /book_ch09/ground_contacts > "$OUT/contact_topic_info.txt" 2>&1 || true
[[ "$CONTACT_READY" == 1 ]] || { echo "CH09_165_CONTACT_TOPIC_NOT_CREATED"; exit 62; }

stage ORIGINAL_STAND_RAMP_PREREQUISITE_NOT_EXISTING_ACCEPTANCE_RETEST
start stand_up ros2 run my_quadruped_bot stand_up
RAMP_DONE=0
for attempt in $(seq 1 180); do
  if grep -q STAND_UP_RAMP_COMPLETE_ORIGINAL_GOALS "$OUT/stand_up.log"; then RAMP_DONE=1; break; fi
  sleep .1
done
[[ "$RAMP_DONE" == 1 ]] || { echo "CH09_165_STAND_RAMP_NOT_COMPLETE"; exit 63; }
grep -q STAND_UP_MEASURED_START_RAMP_6S "$OUT/stand_up.log"

stage CAPTURE_REAL_GROUND_CONTACTS_AFTER_RAMP
set +e
timeout --signal=TERM --kill-after=3s 7s \
  stdbuf -oL gz topic -e -t /book_ch09/ground_contacts \
  > "$OUT/ground_contacts_raw.txt" 2> "$OUT/ground_contacts_stderr.log"
CONTACT_CAPTURE_RC="$?"
set -e
echo "CONTACT_CAPTURE_TIMEOUT_EXIT_RC=$CONTACT_CAPTURE_RC" >> "$OUT/stages.log"
[[ "$CONTACT_CAPTURE_RC" == 124 || "$CONTACT_CAPTURE_RC" == 0 ]] || exit "$CONTACT_CAPTURE_RC"
test -s "$OUT/ground_contacts_raw.txt"

stage INDEPENDENT_FOUR_FOOT_GROUND_CONTACT_PROBE
python3 "$ROOT/ci/docker/ch09_165_verify_ground_contacts.py" \
  "$OUT/ground_contacts_raw.txt" "$OUT/contacts_receipt.json" \
  2>&1 | tee "$OUT/contact_probe.log"
grep -q CH09_165_ACTUAL_FOUR_FOOT_GROUND_CONTACT_PASS "$OUT/contact_probe.log"
stage CH09_165_DIRECT_FOUR_FOOT_CONTACT_SCOPED_PASS
echo "CH09_165_ACTUAL_ORIGINAL_STAND_FOUR_FOOT_CONTACT_PASS_FRICTION_COEFF_NOT_MEASURED" | tee "$OUT/verdict.txt"
