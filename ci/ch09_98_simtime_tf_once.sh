#!/usr/bin/env bash
# Ch09 §9.8: existing Xacro+bridge contract and real RSP TF only.
# No Gazebo physics, stand_up, single_leg_mover or held Ch10.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work; OUT="$ROOT/ci-results/ch09-98"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=98 ROS_LOCALHOST_ONLY=1
printf 'tested_source=%s\nbase_image=%s\n' "${RUN_SOURCE_SHA:-UNKNOWN}" \
 'ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f' > "$OUT/environment.txt"
RSP=; STAGE=INIT
stage(){ STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
cleanup(){
 local rc="$?"; trap - EXIT; set +e
 local shutdown=NOT_STARTED
 if [[ -n "$RSP" ]]; then
   shutdown=SIGTERM_SENT
   kill -TERM -- "-$RSP" 2>/dev/null || true
   local attempt
   for attempt in $(seq 1 30); do
     if ! kill -0 -- "-$RSP" 2>/dev/null; then shutdown=SIGTERM_CLEAN; break; fi
     sleep .1
   done
   if [[ "$shutdown" != SIGTERM_CLEAN ]]; then
     kill -KILL -- "-$RSP" 2>/dev/null || true
     shutdown=SIGKILL_ESCALATION
     if [[ "$rc" == 0 ]]; then rc=75; fi
   fi
 fi
 printf '{"status":"%s","stage":"%s","rc":%d,"shutdown":"%s","real_gazebo":"NOT_RUN","ch10":"HOLD"}\n' \
 "$([[ "$rc" == 0 ]] && echo SCOPED_PASS || echo FAIL)" "$STAGE" "$rc" "$shutdown" > "$OUT/result.json"
 echo "CH09_98_SHUTDOWN=$shutdown rc=$rc" | tee -a "$OUT/stages.log"
 exit "$rc"
}
trap cleanup EXIT
stage BUILD_ORIGINAL_CH09_PACKAGE
cd "$ROOT/Ch09/ros2_ws"
timeout --signal=TERM --kill-after=5s 100s colcon build --symlink-install \
 --packages-select my_quadruped_bot > "$OUT/build.log" 2>&1
set +u; source "$PWD/install/setup.bash"; set -u
ros2 pkg prefix my_quadruped_bot > "$OUT/package_prefix.txt"
python3 -m compileall -q src/my_quadruped_bot/my_quadruped_bot src/my_quadruped_bot/launch
stage ACTUAL_XACRO_JOINT_BRIDGE_AND_MASS_AUDIT
xacro "$(ros2 pkg prefix --share my_quadruped_bot)/urdf/robot.urdf.xacro" \
 > "$OUT/robot.urdf"
check_urdf "$OUT/robot.urdf" > "$OUT/check_urdf.txt"
python3 - "$OUT/robot.urdf" \
 "$(ros2 pkg prefix --share my_quadruped_bot)/config/ros_gz_bridge.yaml" \
 "$OUT/model_contract.json" <<'PY'
import json,sys,xml.etree.ElementTree as E
from pathlib import Path
import yaml
xml=E.parse(sys.argv[1]).getroot()
revolute=[x.attrib["name"] for x in xml.findall("./joint")
          if x.attrib.get("type") in ("revolute","continuous")]
required={f"{leg}_{kind}_joint"
          for leg in ("fr","fl","rr","rl") for kind in ("hip","thigh","calf")}
assert len(revolute)==12 and set(revolute)==required
masses=[float(x.attrib["value"]) for x in xml.findall(".//inertial/mass")]
assert masses and all(x>0 for x in masses), "missing/nonpositive inertial mass"
bridge=yaml.safe_load(Path(sys.argv[2]).read_text())
cmd=[a for a in bridge if a.get("direction")=="ROS_TO_GZ"]
assert len(cmd)==12
assert len({a["ros_topic_name"] for a in cmd})==12
assert len({a["gz_topic_name"] for a in cmd})==12
for j in required:
    entry=[a for a in cmd if a["ros_topic_name"]==
           f"/model/my_quadruped/joint/{j}/cmd_pos"]
    assert len(entry)==1 and entry[0]["gz_topic_name"]==(
      f"/model/my_quadruped/joint/{j}/0/cmd_pos"
    )
    assert entry[0]["ros_type_name"]=="std_msgs/msg/Float64"
assert len([a for a in bridge if a.get("ros_topic_name")=="/clock"])==1
data={"all_12_joint_names":sorted(revolute),"bridge_command_pairs":len(cmd),
      "positive_inertial_masses_count":len(masses),
      "total_inertial_mass_kg":sum(masses),
      "simulator_clock_bridge_present":True,
      "source_physics_unchanged":True}
Path(sys.argv[3]).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
print("CH09_98_REAL_GENERATED_URDF_AND_12_BRIDGE_PAIRS_PASS "
      f"total_mass_kg={data['total_inertial_mass_kg']:.4f}")
PY
stage START_ACTUAL_RSP_WITH_SIM_TIME
python3 - "$OUT/robot.urdf" "$OUT/rsp.yaml" <<'PY'
from pathlib import Path
import yaml,sys
xml=Path(sys.argv[1]).read_text()
Path(sys.argv[2]).write_text(yaml.safe_dump({
  "robot_state_publisher":{"ros__parameters":{
    "robot_description":xml,"use_sim_time":True
  }}
},sort_keys=False))
PY
setsid ros2 run robot_state_publisher robot_state_publisher \
 --ros-args --params-file "$OUT/rsp.yaml" > "$OUT/rsp.log" 2>&1 &
RSP="$!"
stage PUBLISH_SYNTHETIC_CLOCK_AND_12_JOINTS_VERIFY_REAL_TF
export CH09_98_RECEIPT="$OUT/tf_receipt.json"
timeout --signal=TERM --kill-after=5s 32s \
 python3 "$ROOT/ci/ch09_98_tf_probe.py" 2>&1 | tee "$OUT/tf_probe.log"
grep -q CH09_98_ACTUAL_SIMTIME_TF_STATIC_AND_12_DYNAMIC_FRAMES_PASS "$OUT/tf_probe.log"
stage INDEPENDENT_TF_RECEIPT_AUDIT
python3 - "$CH09_98_RECEIPT" <<'PY'
import json,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
assert d["chapter"]=="Ch09" and d["section"]=="9.8"
assert d["status"]=="SCOPED_PASS"
assert d["observed_dynamic_count"]==12
assert d["observed_required_static_count"]==5
assert len(d["joint_names"])==12
assert d["static_frames"]["base_link"]=="base_footprint"
assert all(x["stamp_sec"]>=100 for x in d["dynamic_frames"].values())
assert d["real_gazebo_physics"]==d["stable_stand_retest"]==d["single_leg_sine_retest"]=="NOT_RUN"
assert d["ch10"]=="HOLD"
print("CH09_98_INDEPENDENT_ROS_SIM_CLOCK_TF_RECEIPT_PASS")
PY
stage CH09_98_SIM_TIME_TF_SCOPED_PASS
echo CH09_98_ACTUAL_RSP_SIMTIME_TF_CONTRACT_PASS_NO_GAZEBO_RETEST \
 | tee "$OUT/verdict.txt"
