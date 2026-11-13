#!/usr/bin/env bash
# Ch07 #163: distinct matched-pixel original sensor coordinate proof; prior passing #127/#161 untouched.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT=/work/ci-results/vision/Ch07-163
mkdir -p "$OUT"
export ROS_DOMAIN_ID=69
export GZ_PARTITION="book_optical_${GITHUB_RUN_ID:-local}_$$_$RANDOM"
export GZ_IP=127.0.0.1
export QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless ROS_LOCALHOST_ONLY=1
echo "source_sha=${RUN_SOURCE_SHA:-UNKNOWN}" > "$OUT/environment.txt"
echo "partition=$GZ_PARTITION" >> "$OUT/environment.txt"
STAGE=INIT
OWNED=()
OWNED_NAMES=()
stage() { STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
start() {
  local name="$1"; shift
  # Own the entire child group. Docker --init reaps any detached zombies.
  setsid "$@" > "$OUT/$name.log" 2>&1 &
  OWNED+=("$!")
  OWNED_NAMES+=("$name")
  echo "START:$name:pgid=$!" | tee -a "$OUT/stages.log"
}
group_running() {
  local pgid="$1"
  # Ignore zombie leaders; shell wait() below reaps them.
  ps -eo pgid=,stat= | awk -v g="$pgid" '$1==g && $2 !~ /^Z/ {active=1} END {exit !active}'
}
stop_owned() {
  local pgid="$1" name="$2" original_rc="$3" attempt exit_code
  if [[ "$name" == "gzserver" && "$original_rc" -eq 0 ]]; then
    # Do not deliver SIGINT inside a rendering / gz-transport Publish.
    # Gazebo Harmonic supports a bounded, finite server run via --iterations;
    # let it exit under its own event loop, not the upstream signal handler
    # (gazebosim/gz-sim#4173). This is ONLY a teardown change.
    echo "GAZEBO_FINITE_ITERATIONS_WAIT_BEGIN pgid=$pgid" >> "$OUT/stages.log"
    for attempt in $(seq 1 240); do
      if ! group_running "$pgid"; then
        exit_code=0
        wait "$pgid" || exit_code=$?
        echo "GAZEBO_NATURAL_ITERATIONS_EXIT_RC=$exit_code" >> "$OUT/stages.log"
        [[ "$exit_code" -eq 0 ]]
        return $?
      fi
      sleep .25
    done
    echo "GAZEBO_FINITE_ITERATIONS_TIMEOUT_AFTER_60S pgid=$pgid" >> "$OUT/stages.log"
  fi
  if [[ "$name" == "gzserver" ]] && group_running "$pgid"; then
    # Harmonic plain gz sim can deadlock in the signal handler while a
    # Sensors render thread holds gz-transport locks (upstream #4173).
    # Request an orderly stop from Gazebo's server API BEFORE SIGINT.
    echo "GAZEBO_SERVER_CONTROL_STOP_REQUESTED pgid=$pgid" >> "$OUT/stages.log"
    timeout 5s gz service -s /server_control \
      --reqtype gz.msgs.ServerControl --reptype gz.msgs.Boolean \
      --timeout 1500 --req 'stop: true' \
      > "$OUT/server_control_stop.log" 2>&1 || true
    for attempt in $(seq 1 20); do
      if ! group_running "$pgid"; then
        wait "$pgid" 2>/dev/null || true
        echo "SHUTDOWN_GAZEBO_SERVER_CONTROL_CLEAN name=$name pgid=$pgid" >> "$OUT/stages.log"
        return 0
      fi
      sleep .15
    done
    echo "GAZEBO_SERVER_CONTROL_FALLBACK_SIGNAL pgid=$pgid" >> "$OUT/stages.log"
  fi
  if ! group_running "$pgid"; then
    wait "$pgid" 2>/dev/null || true
    echo "SHUTDOWN_ALREADY_EXITED name=$name pgid=$pgid" >> "$OUT/stages.log"
    return 0
  fi
  kill -INT -- "-$pgid" 2>/dev/null || true
  for attempt in $(seq 1 25); do
    if ! group_running "$pgid"; then
      wait "$pgid" 2>/dev/null || true
      echo "SHUTDOWN_SIGINT_CLEAN name=$name pgid=$pgid" >> "$OUT/stages.log"
      return 0
    fi
    sleep .2
  done
  kill -TERM -- "-$pgid" 2>/dev/null || true
  echo "SHUTDOWN_ESCALATED_TERM name=$name pgid=$pgid" >> "$OUT/stages.log"
  for attempt in $(seq 1 25); do
    if ! group_running "$pgid"; then
      wait "$pgid" 2>/dev/null || true
      echo "SHUTDOWN_SIGTERM_CLEAN name=$name pgid=$pgid" >> "$OUT/stages.log"
      return 0
    fi
    sleep .2
  done
  # Diagnostics first; never promote an upstream shutdown deadlock to PASS.
  ps -eo pid=,ppid=,pgid=,stat=,etime=,comm= |
    awk -v g="$pgid" '$3==g {print}' > "$OUT/shutdown_stuck_${name}.txt" 2>/dev/null || true
  kill -KILL -- "-$pgid" 2>/dev/null || true
  wait "$pgid" 2>/dev/null || true
  echo "SHUTDOWN_ESCALATED_SIGKILL name=$name pgid=$pgid" >> "$OUT/stages.log"
  return 1
}
cleanup() {
  local original_rc="$?"
  local final_rc="$original_rc" idx shutdown="OWNED_GROUPS_EXITED_NO_SIGKILL"
  trap - EXIT
  set +e
  # Never use a variable also used inside stop_owned (Bash dynamic scoping).
  for ((idx=${#OWNED[@]}-1;idx>=0;idx--)); do
    stop_owned "${OWNED[$idx]}" "${OWNED_NAMES[$idx]}" "$original_rc" || shutdown="SIGKILL_ESCALATION"
  done
  if [[ "$shutdown" == "SIGKILL_ESCALATION" && "$final_rc" -eq 0 ]]; then
    final_rc=75
  fi
  if [[ -f "$HOME/.gz/rendering/ogre2.log" ]]; then
    cp -f "$HOME/.gz/rendering/ogre2.log" "$OUT/ogre2.log" 2>/dev/null || true
  fi
  python3 - "$OUT/result.json" "$STAGE" "$original_rc" "$final_rc" "$shutdown" <<'PYRESULT'
import json,sys
from pathlib import Path
out,stage,original,final,shutdown=sys.argv[1:]
record={"chapter":"Ch07","section":"7.2","scope":"OGRE2_MATCHED_PIXEL_OPTICAL_FRAME_DIAGNOSIS",
 "status":"PASS" if int(final)==0 else "FAIL","last_stage":stage,
 "original_exit_code":int(original),"exit_code":int(final),
 "shutdown":shutdown,"renderer":"ogre2","rendering_mode":"official_egl_headless",
 "whole_chapter_accepted":False,"depth_alignment":"NOT_RUN",
 "gazebo_gui":"NOT_RUN","ch10":"HOLD"}
Path(out).write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
PYRESULT
  echo "CH07_163_FINAL stage=$STAGE rc=$final_rc shutdown=$shutdown" | tee -a "$OUT/stages.log"
  exit "$final_rc"
}
trap cleanup EXIT
WS="$ROOT/Ch07/ros2_ws"
stage COLCON_BUILD
cd "$WS"
timeout --signal=TERM --kill-after=8s 105s colcon build --symlink-install --packages-select vision_basics \
  2>&1 | tee "$OUT/colcon.log"
set +u; source install/setup.bash; set -u
ros2 pkg prefix vision_basics > "$OUT/package_prefix.txt"
stage REAL_CAMERA_XACRO
xacro "$WS/src/vision_basics/urdf/my_robot.ros2_camera_gazebo.urdf.xacro" > "$OUT/camera.urdf"
check_urdf "$OUT/camera.urdf" > "$OUT/check_urdf.txt"
grep -q 'name="camera_optical_frame"' "$OUT/camera.urdf"
grep -q 'name="rgbd_camera"' "$OUT/camera.urdf"
stage SINGLE_WORLD_SENSORS_SYSTEM_CONTRACT
python3 - "$OUT/camera.urdf" "$ROOT/ci/docker/fixtures/ch07_camera_world.sdf" "$OUT/sensors_system_contract.json" <<'PY'
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
robot=ET.parse(sys.argv[1]).getroot()
world=ET.parse(sys.argv[2]).getroot()
def sensor_systems(root):
    return [p for p in root.findall('.//plugin')
            if p.attrib.get('name')=='gz::sim::systems::Sensors' and
            p.attrib.get('filename')=='gz-sim-sensors-system']
model_systems=sensor_systems(robot)
world_systems=sensor_systems(world)
rgbd=robot.findall('.//sensor[@type="rgbd_camera"]')
assert len(model_systems)==0, f"CH07_163_DUPLICATE_ROBOT_SENSORS count={len(model_systems)}"
assert len(world_systems)==1, f"CH07_163_WORLD_SENSORS_COUNT={len(world_systems)}"
assert len(rgbd)==1, f"CH07_163_ORIGINAL_RGBD_COUNT={len(rgbd)}"
assert world_systems[0].findtext('render_engine')=='ogre2'
report={"world_sensors_system_count":1,"robot_sensors_system_count":0,
        "original_rgbd_sensor_count":1,"engine":"ogre2"}
Path(sys.argv[3]).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print("CH07_163_SINGLE_WORLD_SENSORS_STATIC_CONTRACT_PASS",flush=True)
PY
stage OFFICIAL_EGL_HEADLESS_RENDERER_PREFLIGHT
# Historical -s/Xvfb variants both SIGABRT. This test changes ONLY the
# official Gazebo rendering mode, not URDF, OGRE2 engine or base-image digest.
unset DISPLAY
export EGL_PLATFORM=surfaceless
{
  echo "rendering_mode=OGRE2_OFFICIAL_EGL_HEADLESS"
  echo "EGL_PLATFORM=$EGL_PLATFORM"
  echo "LIBGL_ALWAYS_SOFTWARE=$LIBGL_ALWAYS_SOFTWARE"
  echo "DISPLAY=${DISPLAY-UNSET}"
  echo "GZ_SIM_RESOURCE_PATH=${GZ_SIM_RESOURCE_PATH-UNSET}"
  ls -l /dev/dri /dev/dxg 2>&1 || true
} >> "$OUT/environment.txt"
timeout 7s gz sim --help > "$OUT/gz_sim_help.txt" 2>&1 || true
if ! grep -q -- '--iterations' "$OUT/gz_sim_help.txt"; then
  echo "CH07_163_GAZEBO_FINITE_ITERATIONS_UNSUPPORTED" | tee "$OUT/preflight_error.txt"
  exit 65
fi
if ! grep -q -- '--headless-rendering' "$OUT/gz_sim_help.txt"; then
  echo "CH07_163_OFFICIAL_HEADLESS_FLAG_UNSUPPORTED" | tee "$OUT/preflight_error.txt"
  exit 64
fi
dpkg-query -W -f='${binary:Package}=${Version}\n' \
  'gz-sim*' 'libgz-rendering*' 'libgz-sensors*' 'libegl*' 'libgl1-mesa*' 'libogre*' \
  > "$OUT/renderer_packages.txt" 2>&1 || true
for diagnostic in eglinfo glxinfo; do
  if command -v "$diagnostic" >/dev/null 2>&1; then
    timeout 6s "$diagnostic" > "$OUT/${diagnostic}.txt" 2>&1 || true
  fi
done
stage ROBOT_DESCRIPTION_TF
python3 - "$OUT/camera.urdf" "$OUT/robot_description.yaml" <<'PY'
import sys
from pathlib import Path
import yaml
xml=Path(sys.argv[1]).read_text()
Path(sys.argv[2]).write_text(yaml.safe_dump(
    {"robot_state_publisher":{"ros__parameters":{
        "robot_description":xml,"use_sim_time":True}}},sort_keys=False))
PY
start rsp ros2 run robot_state_publisher robot_state_publisher \
  --ros-args --params-file "$OUT/robot_description.yaml"
stage DEPTH_ONLY_VISIBLE_TARGET_FIXTURE
# Unmodified book fixture keeps its original target at z=1 m, below the
# zero-joint camera's approximate z=2.29 m; all sampled Depth/XYZ invalid.
# Only this TEST-ONLY temp fixture moves the existing visual target into FOV.
# The original SDF blob is untouched and preserved in workflow evidence.
python3 - "$ROOT/ci/docker/fixtures/ch07_camera_world.sdf" "$OUT/depth_probe_world.sdf" "$OUT/depth_fixture_diff.json" <<'PYDEPTHWORLD'
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
source=Path(sys.argv[1]); dst=Path(sys.argv[2])
tree=ET.parse(source)
target=tree.find(".//model[@name='visual_target']/pose")
if target is None or " ".join((target.text or "").split()) != "1 0 1 0 0 0":
    raise RuntimeError("CH07_163_ORIGINAL_TEST_TARGET_CHANGED")
target.text="1 0 2.29 0 0 0"
tree.write(dst,encoding="unicode",xml_declaration=True)
record={"fixture":"TEST_ONLY_VISIBLE_TARGET", "original_sdf":str(source),
        "original_target_pose":"1 0 1 0 0 0",
        "test_target_pose":"1 0 2.29 0 0 0",
        "actual_depth_alignment":"NOT_RUN",
        "book_world_unchanged":True}
Path(sys.argv[3]).write_text(json.dumps(record,indent=2)+"\n")
print("CH07_163_TEST_ONLY_TARGET_FOV_SHIFT_RECORDED",flush=True)
PYDEPTHWORLD
stage GAZEBO_WORLD
# Running a finite number of physics iterations avoids the upstream
# intermittent SIGINT -> Sensors render-thread shutdown deadlock. 12 seconds
# of simulated time is safely longer than the original 3-image smoke period.
start gzserver gz sim -s -r -v 4 --headless-rendering --iterations 12000 "$OUT/depth_probe_world.sdf"
READY=0
for attempt in $(seq 1 30); do
  if timeout 4s gz service -l | grep -Fq /world/book_camera/create; then READY=1; break; fi
  sleep .5
done
[[ "$READY" -eq 1 ]] || { echo "CAMERA_WORLD_SERVICE_MISSING"; exit 1; }
stage GAZEBO_SPAWN
timeout --signal=TERM --kill-after=5s 40s \
  ros2 run ros_gz_sim create -world book_camera -name my_robot \
  -file "$OUT/camera.urdf" -z 0.15 2>&1 | tee "$OUT/create.log"
grep -q 'Entity creation successful' "$OUT/create.log"
stage INDEPENDENT_GAZEBO_SENSORS_LOAD_COUNT
# Preserve full gzserver.log. The previous crash had 2 Sensors systems and
# an identical OGRE HLMS Datablock hash; the fixed world must load exactly 1.
python3 - "$OUT/gzserver.log" "$OUT/sensors_runtime_count.json" <<'PY'
import json,re,sys
from pathlib import Path
text=Path(sys.argv[1]).read_text(errors='replace')
text=re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
count=len(re.findall(r'Loaded system \[gz::sim::systems::Sensors\]',text))
Path(sys.argv[2]).write_text(json.dumps({"loaded_sensors_systems":count},
                                          indent=2,sort_keys=True)+"\n")
if count != 1:
    raise RuntimeError(f"CH07_163_RUNTIME_SENSORS_DUPLICATED count={count}")
print("CH07_163_EXACTLY_ONE_RUNTIME_SENSORS_SYSTEM_PASS",flush=True)
PY
stage SPLIT_BRIDGES_OPTICAL_IMAGE_NATIVE_CAMERA_LINK_POINTS
# Images / CameraInfo / depth retain their validated optical frame header.
start bridge_images ros2 run ros_gz_bridge parameter_bridge \
  '/camera/image@sensor_msgs/msg/Image[gz.msgs.Image' \
  '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo' \
  '/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image' \
  --ros-args -r /camera/image:=/camera/image_raw
# Gazebo PointCloudPacked XYZ is native +X forward. Relabel only this
# GZ->ROS point-cloud bridge to camera_link; DO NOT modify XYZ bytes.
# camera_link -> camera_optical_frame static TF already exists.
start bridge_points ros2 run ros_gz_bridge parameter_bridge \
  '/camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked' \
  --ros-args -p override_frame_id:=camera_link
timeout 10s gz topic -l > "$OUT/gz_topics.txt" || true
for topic in /camera/image /camera/camera_info /camera/depth_image /camera/points; do
  grep -Fxq "$topic" "$OUT/gz_topics.txt" || { echo "CH07_163_GZ_TOPIC_MISSING:$topic"; exit 62; }
done
stage MATCHED_STAMP_PIXEL_OPTICAL_VALIDATION
timeout --signal=TERM --kill-after=5s 42s \
  python3 "$ROOT/ci/docker/ch07_163_sync_optical_probe.py" "$OUT/optical_pixel_receipt.json" \
  2>&1 | tee "$OUT/optical_pixel_probe.log"
grep -q CH07_163_MATCHED_PIXEL_CAMERA_LINK_NATIVE_X_FORWARD_CONFIRMED "$OUT/optical_pixel_probe.log"
stage CH07_163_POINTCLOUD_FRAME_CONTRACT_SCOPED_PASS
echo "CH07_163_GAZEBO_NATIVE_POINTS_CAMERA_LINK_AND_OPTICAL_DEPTH_TF_MATCH_PASS" | tee "$OUT/verdict.txt"
