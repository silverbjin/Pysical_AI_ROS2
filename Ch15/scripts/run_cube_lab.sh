#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# == 1 ]] || { echo 'usage: bash run_cube_lab.sh NEW_EVIDENCE_DIR'; exit 2; }
out="$(realpath -m "$1")"; [[ ! -e "$out" ]] || { echo 'new evidence directory required'; exit 2; };mkdir -p "$out"
: "${ROS_DOMAIN_ID:?dedicated ROS_DOMAIN_ID required}"
export GZ_IP=127.0.0.1 GZ_PARTITION="ch15_cube_$$" ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export QT_QPA_PLATFORM=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
unset DISPLAY
stage=init
pids=();names=();gz_pid=
cleanup(){
  rc=$?
  trap - EXIT INT TERM
  set +e
  for ((i=${#pids[@]}-1;i>=0;i--)); do
    pid="${pids[i]}";name="${names[i]}";forced=0
    if kill -0 "$pid" 2>/dev/null; then
      if [[ "$name" == gazebo ]]; then
        timeout 5s gz service -s /server_control --reqtype gz.msgs.ServerControl --reptype gz.msgs.Boolean --timeout 1500 --req 'stop: true' > "$out/server-stop.log" 2>&1
      else kill -INT -- "-$pid" 2>/dev/null;fi
    fi
    for j in $(seq 1 100);do kill -0 "$pid" 2>/dev/null || break;sleep .1;done
    if kill -0 "$pid" 2>/dev/null;then forced=1;kill -TERM -- "-$pid" 2>/dev/null;sleep .5;if kill -0 "$pid" 2>/dev/null;then kill -KILL -- "-$pid" 2>/dev/null;fi;fi
    wait "$pid";ec=$?
    printf '%s\t%s\t%s\n' "$name" "$ec" "$forced" >>"$out/shutdown.tsv"
    if ((ec || forced));then rc=1;fi
  done
  printf '{"result":"%s","stage":"%s","exit_code":%d,"full_mission_success":false}\n' "$(if ((rc==0));then echo PASS;else echo FAIL;fi)" "$stage" "$rc" > "$out/result.json"
  cat "$out/shutdown.tsv" "$out/result.json" 2>/dev/null
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
start(){ local name="$1";shift;setsid "$@" >"$out/$name.log" 2>&1 & pids+=("$!");names+=("$name");if [[ "$name" == gazebo ]];then gz_pid="$!";fi; }
world="$here/ros2_ws/src/ch15_simulation/worlds/fetch_carry.sdf"
sha256sum "$world" "$here/config/cube_acceptance.json" >"$out/input-sha256.txt"
gz sdf -k "$world" | tee "$out/sdf-check.log"
stage=gazebo
start gazebo gz sim -s -r -v 4 --headless-rendering "$world"
ready=0
for i in $(seq 1 25);do
  kill -0 "$gz_pid" || break
  if timeout 3s gz topic -l >"$out/gz-topics.txt" && grep -Fxq /ch15/cube/rgbd/image "$out/gz-topics.txt" && grep -Fxq /ch15/cube/rgbd/depth_image "$out/gz-topics.txt" && grep -Fxq /ch15/cube/rgbd/camera_info "$out/gz-topics.txt";then ready=1;break;fi
  sleep 1
done
[[ "$ready" == 1 ]]
stage=bridge
start bridge ros2 run ros_gz_bridge parameter_bridge \
 '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock' \
 '/ch15/cube/rgbd/image@sensor_msgs/msg/Image[gz.msgs.Image' \
 '/ch15/cube/rgbd/depth_image@sensor_msgs/msg/Image[gz.msgs.Image' \
 '/ch15/cube/rgbd/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo' \
 --ros-args -p override_frame_id:=camera_optical \
 -r /ch15/cube/rgbd/image:=/camera/image_raw \
 -r /ch15/cube/rgbd/depth_image:=/camera/depth/image_raw \
 -r /ch15/cube/rgbd/camera_info:=/camera/camera_info
start tf ros2 run tf2_ros static_transform_publisher --x 0.6 --y 0 --z 0.5 --qx -0.54517403 --qy 0.54517403 --qz -0.45031686 --qw 0.45031686 --frame-id map --child-frame-id camera_optical
stage=detector
start detector "$(ros2 pkg prefix ch15_simulation)/lib/ch15_simulation/cube_detector" --ros-args -p use_sim_time:=true -p allow_invalid_depth_fixture:=true
stage=witness
timeout --signal=INT --kill-after=10s 160s python3 "$here/tests/g04_cube_witness.py" "$out" "$here/config/cube_acceptance.json"
stage=complete
