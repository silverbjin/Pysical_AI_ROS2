#!/usr/bin/env bash
# Ch07 #127: original RGBD Xacro + OGRE2, official --headless-rendering EGL.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT=/work/ci-results/vision/Ch07
mkdir -p "$OUT"
export ROS_DOMAIN_ID=67
export GZ_PARTITION="book_camera_${GITHUB_RUN_ID:-local}_$$_$RANDOM"
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
  local pgid="$1" name="$2" attempt
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
    stop_owned "${OWNED[$idx]}" "${OWNED_NAMES[$idx]}" || shutdown="SIGKILL_ESCALATION"
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
record={"chapter":"Ch07","section":"7.2","scope":"OGRE2_ORIGINAL_RGBD_OFFICIAL_EGL_HEADLESS",
 "status":"PASS" if int(final)==0 else "FAIL","last_stage":stage,
 "original_exit_code":int(original),"exit_code":int(final),
 "shutdown":shutdown,"renderer":"ogre2","rendering_mode":"official_egl_headless",
 "whole_chapter_accepted":False,"depth_alignment":"NOT_RUN",
 "gazebo_gui":"NOT_RUN","ch10":"HOLD"}
Path(out).write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
PYRESULT
  echo "CH07_127_FINAL stage=$STAGE rc=$final_rc shutdown=$shutdown" | tee -a "$OUT/stages.log"
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
if ! grep -q -- '--headless-rendering' "$OUT/gz_sim_help.txt"; then
  echo "CH07_127_OFFICIAL_HEADLESS_FLAG_UNSUPPORTED" | tee "$OUT/preflight_error.txt"
  exit 64
fi
dpkg-query -W -f='${binary:Package}=\${Version}\n' \
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
stage GAZEBO_WORLD
start gzserver gz sim -s -r -v 4 --headless-rendering "$ROOT/ci/docker/fixtures/ch07_camera_world.sdf"
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
stage CAMERA_BRIDGE
start bridge ros2 run ros_gz_bridge parameter_bridge \
  '/camera/image@sensor_msgs/msg/Image[gz.msgs.Image' \
  '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo' \
  --ros-args -r /camera/image:=/camera/image_raw
timeout 10s gz topic -l > "$OUT/gz_topics.txt" || true
stage MEASURE_IMAGE_INTRINSICS_OPTICAL_TF
timeout --signal=TERM --kill-after=5s 35s \
  python3 "$ROOT/ci/docker/verify_camera.py" "$OUT/camera_data.json" \
  2>&1 | tee "$OUT/camera_probe.log"
grep -q BOOK_CH07_CAMERA_PASS "$OUT/camera_probe.log"
stage CAMERA_PASS
echo "CH07_127_ORIGINAL_OGRE2_OFFICIAL_EGL_IMAGE_INTRINSICS_TF_PASS_GUI_NOT_RUN" | tee "$OUT/verdict.txt"
