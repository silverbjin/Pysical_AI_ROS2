#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=init
pids=()
names=()
gz_pid=
cleanup(){
  rc=$?
  trap - EXIT
  set +e
  # Stop owned server via Gazebo's normal service first.
  if [[ -n "$gz_pid" ]] && kill -0 "$gz_pid" 2>/dev/null; then
    timeout 5s gz service -s /server_control --reqtype gz.msgs.ServerControl --reptype gz.msgs.Boolean --timeout 1500 --req 'stop: true' > "$out/server-stop.log" 2>&1
  fi
  for ((i=${#pids[@]}-1;i>=0;i--)); do
    pid="${pids[i]}"; name="${names[i]}"
    forced=0
    if [[ "$pid" != "$gz_pid" ]] && kill -0 "$pid" 2>/dev/null; then kill -INT -- "-$pid" 2>/dev/null; fi
    for j in $(seq 1 100);do kill -0 "$pid" 2>/dev/null || break; sleep .1;done
    if kill -0 "$pid" 2>/dev/null;then
      forced=1;kill -TERM -- "-$pid" 2>/dev/null;sleep .5
      if kill -0 "$pid" 2>/dev/null;then kill -KILL -- "-$pid" 2>/dev/null;fi
    fi
    wait "$pid";exitcode=$?
    printf '%s\t%s\t%s\n' "$name" "$exitcode" "$forced" >> "$out/shutdown.tsv"
    if ((forced || exitcode!=0));then rc=1;fi
  done
  printf '{"status":"%s","stage":"%s","exit_code":%d,"scope":"G03_L2_ACTUAL_GAZEBO"}\n' "$(if ((rc==0));then echo PASS;else echo FAIL;fi)" "$stage" "$rc" > "$out/result.json"
  exit "$rc"
}
trap cleanup EXIT
start(){
  local name="$1";shift
  setsid "$@" > "$out/$name.log" 2>&1 &
  pids+=("$!");names+=("$name")
  if [[ "$name" == gazebo ]];then gz_pid="$!";fi
}
export DEBIAN_FRONTEND=noninteractive PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg YOLO_CONFIG_DIR=/tmp/ch14-ultralytics
export ROS_DOMAIN_ID=72 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST GZ_IP=127.0.0.1 GZ_PARTITION="ch14_g03_${GITHUB_RUN_ID:-local}_$$"
export QT_QPA_PLATFORM=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
unset DISPLAY
stage=environment
apt-get update -qq
apt-get install -y --no-install-recommends python3-venv python3-pip ros-jazzy-cv-bridge ros-jazzy-vision-msgs ros-jazzy-message-filters ros-jazzy-tf2-ros-py ros-jazzy-diagnostic-msgs ros-jazzy-rosgraph-msgs ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-ament-cmake ros-jazzy-ros-gz-bridge ros-jazzy-ros-gz-sim ros-jazzy-tf2-ros >/dev/null
python3 -m venv --system-site-packages /tmp/ch14-venv
source /tmp/ch14-venv/bin/activate
set +u
source /opt/ros/jazzy/setup.bash
set -u
lock=/ch14/requirements/cpu.lock.txt
# Exact cache from successful G00; fallback to pinned downloads only on missing wheels.
if ! python -m pip download --no-index --find-links /wheelhouse --require-hashes --no-deps --only-binary=:all: -d /wheelhouse -r "$lock"; then
 grep -E '^torch(vision)?==' "$lock" >/tmp/torch.lock
 python -m pip download --require-hashes --no-deps --only-binary=:all: --index-url https://download.pytorch.org/whl/cpu -d /wheelhouse -r /tmp/torch.lock
 python -m pip download --require-hashes --no-deps --only-binary=:all: --find-links /wheelhouse -d /wheelhouse -r "$lock"
fi
python /ch14/scripts/g00_make_wheel_lock.py /wheelhouse "$out"
cmp "$lock" "$out/cpu.candidate.lock.txt"
python -m pip install --ignore-installed --no-deps --no-index --find-links /wheelhouse --require-hashes -r "$lock"
python -m pip check
export PYTHONPATH=/ch14/ros2_ws/src/ch14_ai_common:${PYTHONPATH:-}
stage=colcon
mkdir -p /tmp/ch14-build/src
cp -a /ch14/ros2_ws/src/{ch14_ai_common,ch14_ai_interfaces,ch14_ai_perception,ch14_simulation} /tmp/ch14-build/src/
cd /tmp/ch14-build
python "$(command -v colcon)" build --packages-select ch14_ai_common ch14_ai_interfaces ch14_ai_perception ch14_simulation 2>&1 | tee "$out/colcon-build.log"
unset PYTHONPATH
set +u
source /opt/ros/jazzy/setup.bash
source /tmp/ch14-build/install/setup.bash
set -u
ros2 launch ch14_simulation semantic_rgbd.launch.py --show-args > "$out/launch-args.txt"
stage=model
cd /ch14
python scripts/fetch_models.py yolov8n --cache /tmp/models --fetch --acknowledge-agpl
python python/export_yolo.py --manifest models/model_manifest.json --cache /tmp/models --model yolov8n --output /tmp/yolov8n --threads 1
cp /tmp/yolov8n/export.json "$out/yolov8n-export.json"
sha="$(python -c 'import json;print(json.load(open("/tmp/yolov8n/export.json"))["onnx_sha256"])')"
stage=scene
export GZ_SIM_RESOURCE_PATH=/assets
world=/tmp/ch14-build/install/ch14_simulation/share/ch14_simulation/worlds/semantic_rgbd.sdf
sha256sum "$world" > "$out/world-sha256.txt"
start gazebo gz sim -s -r -v 4 --headless-rendering "$world"
ready=0
for i in $(seq 1 25);do
  if ! kill -0 "$gz_pid";then break;fi
  if timeout 3s gz topic -l > "$out/gz_topics.txt" && grep -Fxq /ch14/rgbd/image "$out/gz_topics.txt" && grep -Fxq /ch14/rgbd/depth_image "$out/gz_topics.txt";then ready=1;break;fi
  sleep 1
done
[[ "$ready" == 1 ]]
timeout 8s gz model --list > "$out/gz_models.txt"
grep -q semantic_person "$out/gz_models.txt"
stage=bridge
start bridge ros2 run ros_gz_bridge parameter_bridge \
  '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock' \
  '/ch14/rgbd/image@sensor_msgs/msg/Image[gz.msgs.Image' \
  '/ch14/rgbd/depth_image@sensor_msgs/msg/Image[gz.msgs.Image' \
  '/ch14/rgbd/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo' \
  --ros-args -p override_frame_id:=camera_optical \
  -r /ch14/rgbd/image:=/camera/color/image_raw \
  -r /ch14/rgbd/depth_image:=/camera/aligned_depth_to_color/image_raw \
  -r /ch14/rgbd/camera_info:=/camera/color/camera_info
start tf ros2 run tf2_ros static_transform_publisher --x 0 --y 0 --z 1 --roll -1.5707963267948966 --pitch 0 --yaw -1.5707963267948966 --frame-id odom --child-frame-id camera_optical
sleep 1
stage=actual_witness
start detector /tmp/ch14-build/install/ch14_ai_perception/lib/ch14_ai_perception/detector_node --ros-args \
  -p onnx:=/tmp/yolov8n/yolov8n.onnx -p model_sha256:="$sha" -p use_sim_time:=true -p rgbd:=true \
  -p target_class:=person -p target_frame:=odom -p trace_inputs:=true
timeout --signal=INT --kill-after=5s 100s python scripts/g03_gazebo_witness.py --out "$out"
stage=complete
