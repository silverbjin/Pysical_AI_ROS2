#!/usr/bin/env bash
# SIMULATION ONLY. Run the book's actual RGBD Xacro in an isolated headless world.
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
stage() { STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
start() {
  local name="$1"; shift
  "$@" > "$OUT/$name.log" 2>&1 &
  OWNED+=("$!")
  echo "START:$name:pid=$!" | tee -a "$OUT/stages.log"
}
stop_owned() {
  local pid="$1"
  kill -INT "$pid" 2>/dev/null || true
  for i in $(seq 1 12); do
    if ! kill -0 "$pid" 2>/dev/null; then wait "$pid" 2>/dev/null || true; return; fi
    sleep .15
  done
  echo "SHUTDOWN_ESCALATED_TERM pid=$pid" | tee -a "$OUT/stages.log"
  kill -TERM "$pid" 2>/dev/null || true
  for i in $(seq 1 12); do
    if ! kill -0 "$pid" 2>/dev/null; then wait "$pid" 2>/dev/null || true; return; fi
    sleep .15
  done
  kill -KILL "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}
cleanup() {
  local code="$?"
  trap - EXIT
  set +e
  for ((i=${#OWNED[@]}-1;i>=0;i--)); do stop_owned "${OWNED[$i]}"; done
  printf '{"chapter":"Ch07","scope":"CAMERA_GAZEBO_TO_ROS_HEADLESS","status":"%s","exit_code":%d,"last_stage":"%s","whole_chapter_accepted":false}\n' \
    "$([[ "$code" -eq 0 ]] && echo PASS || echo FAIL)" "$code" "$STAGE" > "$OUT/result.json"
  exit "$code"
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
start gzserver gz sim -s -r -v 2 "$ROOT/ci/docker/fixtures/ch07_camera_world.sdf"
READY=0
for i in $(seq 1 30); do
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
echo "CH07_CAMERA_IMAGE_INTRINSICS_TF_PASS_GUI_NOT_RUN" | tee "$OUT/verdict.txt"
