#!/usr/bin/env bash
# Headless SIMULATION ONLY: Ch05 controller motion and Ch09-Ch11 Gazebo spawn.
set -Eeuo pipefail
set +u
source /opt/ros/jazzy/setup.bash
set -u
CH="$1"
case "$CH" in
  Ch05) export ROS_DOMAIN_ID=85 ;;
  Ch09) export ROS_DOMAIN_ID=89 ;;
  Ch10) export ROS_DOMAIN_ID=90 ;;
  Ch11) export ROS_DOMAIN_ID=91 ;;
  *) echo "Unknown chapter: $CH" >&2; exit 2 ;;
esac
OUT="/work/ci-results/next/$CH"
mkdir -p "$OUT"
export GZ_PARTITION="book_$CH-$GITHUB_RUN_ID-$$-$RANDOM"
export GZ_IP=127.0.0.1
export QT_QPA_PLATFORM=offscreen
export LIBGL_ALWAYS_SOFTWARE=1
export ROS_LOCALHOST_ONLY=1
echo "source_sha=$RUN_SOURCE_SHA" > "$OUT/env.txt"
echo "GZ_PARTITION=$GZ_PARTITION" >> "$OUT/env.txt"
STAGE=START
BG=""
stage() { STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
stop_pid() {
  pid="$1"; kill -INT "$pid" 2>/dev/null || true
  for i in $(seq 1 15); do
    if ! kill -0 "$pid" 2>/dev/null; then wait "$pid" 2>/dev/null || true; return; fi
    sleep .1
  done
  echo "TERM_ESCALATION:$pid" | tee -a "$OUT/stages.log"
  kill -TERM "$pid" 2>/dev/null || true
  for i in $(seq 1 15); do
    if ! kill -0 "$pid" 2>/dev/null; then wait "$pid" 2>/dev/null || true; return; fi
    sleep .1
  done
  echo "KILL_ESCALATION:$pid" | tee -a "$OUT/stages.log"
  kill -KILL "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}
cleanup() {
  rc="$?"
  trap - EXIT
  set +e
  for pid in $BG; do stop_pid "$pid"; done
  printf '{"chapter":"%s","source_sha":"%s","exit_code":%d,"last_stage":"%s","chapter_accepted":false}\n' "$CH" "$RUN_SOURCE_SHA" "$rc" "$STAGE" > "$OUT/result.json"
  exit "$rc"
}
trap cleanup EXIT
start() {
  name="$1"; shift
  "$@" > "$OUT/$name.log" 2>&1 &
  BG="$! $BG"
  echo "START:$name:$!" | tee -a "$OUT/stages.log"
}
ready_world() {
  world="$1"
  for i in $(seq 1 30); do
    if timeout 4s gz service -l 2>/dev/null | grep -Fq "/world/$world/create"; then return 0; fi
    sleep .5
  done
  echo "WORLD_SERVICE_MISSING:$world" >&2
  return 1
}
ready_manager() {
  for i in $(seq 1 40); do
    if timeout 4s ros2 service list 2>/dev/null | grep -Fxq /controller_manager/list_controllers; then return 0; fi
    sleep .5
  done
  echo "CONTROLLER_MANAGER_MISSING" >&2
  return 1
}
if [[ "$CH" == Ch05 ]]; then PKG=manipulation_basics; else PKG=my_quadruped_bot; fi
WS="/work/$CH/ros2_ws"
cd "$WS"
stage COLCON_BUILD
timeout --signal=TERM --kill-after=8s 145s colcon build --symlink-install --packages-up-to "$PKG" 2>&1 | tee "$OUT/colcon.log"
set +u
source install/setup.bash
set -u
ros2 pkg prefix "$PKG" | tee "$OUT/prefix.txt"
stage XACRO_CHECK
xacro "$WS/src/$PKG/urdf/robot.urdf.xacro" > "$OUT/robot.urdf"
if [[ "$CH" == Ch09 && "${BOOK_STANCE:-0}" == 1 ]]; then
  stage CH09_CI_INSTRUMENT_ODOMETRY_ONLY
  python3 /work/ci/docker/instrument_ch09_odom.py "$OUT/robot.urdf" \
    2>&1 | tee "$OUT/ci_instrumentation.log"
fi
check_urdf "$OUT/robot.urdf" > "$OUT/urdf.txt"
if [[ "$CH" == Ch05 ]]; then
  python3 /work/ci/docker/verify_urdf_joints.py "$OUT/robot.urdf" joint1 joint2 joint3 joint4 | tee "$OUT/joint_contract.txt"
  stage CH05_ROBOT_DESCRIPTION
  # Original GUI launch starts robot_state_publisher BEFORE spawn; its transient
  # robot_description unblocks gz_ros2_control resource-manager initialization.
  python3 - "$OUT/robot.urdf" "$OUT/rsp.yaml" <<'PY'
from pathlib import Path
import sys
import yaml
description = Path(sys.argv[1]).read_text(encoding="utf-8")
Path(sys.argv[2]).write_text(yaml.safe_dump({
    "robot_state_publisher": {"ros__parameters": {
        "robot_description": description,
        "use_sim_time": True
    }}
}, sort_keys=False), encoding="utf-8")
PY
  start rsp ros2 run robot_state_publisher robot_state_publisher     --ros-args --params-file "$OUT/rsp.yaml"
  WORLD=empty
  SOURCE_WORLD=empty.sdf
  ROBOT=physical_ai_robot
  SPAWN_Z=0.05
else
  python3 /work/ci/docker/verify_urdf_joints.py "$OUT/robot.urdf" fr_hip_joint fr_thigh_joint fr_calf_joint fl_hip_joint fl_thigh_joint fl_calf_joint rr_hip_joint rr_thigh_joint rr_calf_joint rl_hip_joint rl_thigh_joint rl_calf_joint | tee "$OUT/joint_contract.txt"
  WORLD=my_empty_world
  SOURCE_WORLD="$WS/src/$PKG/worlds/empty_world.sdf"
  if [[ "$CH" == Ch11 && ( "${BOOK_DYNAMIC:-0}" == 1 || "${BOOK_LOCALIZATION:-0}" == 1 ) ]]; then
    WORLD=sensor_figure_world
    SOURCE_WORLD="$WS/src/$PKG/worlds/sensor_figure_world.sdf"
  fi
  ROBOT=my_quadruped
  SPAWN_Z=0.5
fi
stage GAZEBO_WORLD
start gazeboserver gz sim -s -r -v 2 "$SOURCE_WORLD"
ready_world "$WORLD"
stage ENTITY_SPAWN
timeout --signal=TERM --kill-after=4s 40s ros2 run ros_gz_sim create -world "$WORLD" -name "$ROBOT" -file "$OUT/robot.urdf" -z "$SPAWN_Z" 2>&1 | tee "$OUT/spawn.log"
grep -q 'Entity creation successful' "$OUT/spawn.log"
stage CLOCK_BRIDGE
start bridge ros2 run ros_gz_bridge parameter_bridge '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
timeout --signal=TERM --kill-after=3s 30s ros2 topic echo /clock --once > "$OUT/clock.txt"
grep -q 'sec:' "$OUT/clock.txt"

if [[ "$CH" != Ch05 ]]; then
  if [[ "$CH" == Ch09 && "${BOOK_STANCE:-0}" == "1" ]]; then
    stage CH09_ORIGINAL_JOINT_BRIDGE
    start stance_joint_bridge ros2 run ros_gz_bridge parameter_bridge \
      --ros-args -p config_file:="$WS/src/$PKG/config/ros_gz_bridge.yaml"
    stage CH09_GAZEBO_BASE_OBSERVATION
    start stance_odom_bridge ros2 run ros_gz_bridge parameter_bridge \
      '/model/my_quadruped/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry' \
      --ros-args -r /model/my_quadruped/odometry:=/stand_observation/odom
    stage CH09_ORIGINAL_STAND_UP
    start stand_up ros2 run my_quadruped_bot stand_up
    stage CH09_LATE_WINDOW_TILT_HEIGHT_DRIFT
    timeout --signal=TERM --kill-after=4s 30s \
      python3 /work/ci/docker/verify_ch09_stance.py "$OUT/stance_verdict.json" \
      2>&1 | tee "$OUT/stance_probe.log"
    grep -q CH09_POSTURE_STABILITY_PASS "$OUT/stance_probe.log"
    stage CH09_POSTURE_SCOPED_PASS
    echo 'CH09_POSTURE_PROXY_PASS_FOOT_CONTACT_NOT_TESTED' | tee "$OUT/verdict.txt"
    exit 0
  fi
  if [[ "$CH" == Ch11 && "${BOOK_LOCALIZATION:-0}" == "1" ]]; then
    stage CH11_REAL_ROBOT_DESCRIPTION
    python3 - "$OUT/robot.urdf" "$OUT/robot_description.yaml" <<'PY'
from pathlib import Path
import sys
import yaml
xml=Path(sys.argv[1]).read_text()
Path(sys.argv[2]).write_text(yaml.safe_dump(
  {'robot_state_publisher':{'ros__parameters':{
  'robot_description':xml,'use_sim_time':True}}},sort_keys=False))
PY
    start rsp ros2 run robot_state_publisher robot_state_publisher \
      --ros-args --params-file "$OUT/robot_description.yaml"
    stage CH11_ORIGINAL_SENSOR_BRIDGE
    start localization_bridge ros2 run ros_gz_bridge parameter_bridge \
      --ros-args -p config_file:="$WS/src/$PKG/config/ros_gz_bridge.yaml"
    stage CH11_SIM_OBSERVATION_ADAPTER
    start sim_odometry ros2 run my_quadruped_bot sim_odometry
    stage CH11_EKF_FUSION
    start ekf ros2 run robot_localization ekf_node \
      --ros-args -r __node:=ekf_filter_node \
      --params-file "$WS/src/$PKG/config/ekf.yaml" \
      -r /odometry/filtered:=/odom
    stage CH11_ORIGINAL_SCAN_GATE
    start scan_gate ros2 run my_quadruped_bot slam_scan_filter \
      --ros-args -p use_sim_time:=true
    stage CH11_SLAM_TOOLBOX_NO_GUI
    start slam_launch ros2 launch my_quadruped_bot slam.launch.py \
      start_rviz:=false start_scan_filter:=false
    stage CH11_OBSERVED_EKF_TF_SCAN
    timeout --signal=TERM --kill-after=4s 46s \
      python3 /work/ci/docker/verify_localization.py "$OUT/localization.json" \
      2>&1 | tee "$OUT/localization.log"
    grep -q 'BOOK_CH11_LOCALIZATION_PASS' "$OUT/localization.log"
    stage CH11_SLAM_LIFECYCLE
    timeout 14s ros2 lifecycle get /slam_toolbox \
      2>&1 | tee "$OUT/slam_lifecycle.txt"
    grep -qi 'active' "$OUT/slam_lifecycle.txt"
    if [[ "${BOOK_MAP_SAVE:-0}" == "1" ]]; then
      stage CH11_MAP_SAVE_SERVICE_DISCOVERY
      FOUND=0
      for i in $(seq 1 20); do
        if timeout 4s ros2 service list -t \
          | grep -Fq '/slam_toolbox/save_map [slam_toolbox/srv/SaveMap]'; then
          FOUND=1; break
        fi
        sleep .3
      done
      [[ "$FOUND" -eq 1 ]] || { echo 'CH11_MAP_SAVE_SERVICE_MISSING'; exit 1; }
      stage CH11_REAL_SAVE_MAP_REQUEST
      timeout --signal=TERM --kill-after=5s 38s \
        ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
          "{name: {data: '$OUT/book_ch11_map'}}" \
        2>&1 | tee "$OUT/save_map_service.log"
      stage CH11_SAVED_MAP_FILES_AND_PIXELS
      python3 /work/ci/docker/verify_ch11_saved_map.py \
        "$OUT" book_ch11_map 2>&1 | tee "$OUT/map_save_probe.log"
      grep -q CH11_MAP_SAVE_FILES_AND_PIXELS_PASS "$OUT/map_save_probe.log"
      stage CH11_MAP_SAVE_SCOPED_PASS
      echo 'CH11_MAP_SAVE_PIXELS_PASS_ACCURACY_NOT_RUN' | tee "$OUT/verdict.txt"
      exit 0
    fi
    stage CH11_LOCALIZATION_SCOPED_PASS
    echo 'CH11_EKF_TF_SCAN_SLAM_ACTIVE_PASS_MAP_SAVE_NOT_RUN' \
      | tee "$OUT/verdict.txt"
    exit 0
  fi
  if [[ "${BOOK_EXTENDED:-0}" == "1" ]]; then
    if [[ "$CH" == Ch09 ]]; then
      stage EXTENDED_CH09_BRIDGE
      start joint_bridge ros2 run ros_gz_bridge parameter_bridge \
        --ros-args -p config_file:="$WS/src/$PKG/config/ros_gz_bridge.yaml"
      stage EXTENDED_CH09_PROBE_LISTEN_FIRST
      timeout --signal=TERM --kill-after=4s 24s \
        python3 /work/ci/docker/verify_extended.py ch09 "$OUT/extended.json" \
        > "$OUT/extended.log" 2>&1 &
      CHECK_PID="$!"
      BG="$CHECK_PID $BG"
      sleep 2
      stage EXTENDED_CH09_ORIGINAL_STAND_UP
      start stand_up ros2 run my_quadruped_bot stand_up
      wait "$CHECK_PID"
      cat "$OUT/extended.log"
      grep -q 'BOOK_EXTENDED_CH09_PASS' "$OUT/extended.log"
    elif [[ "$CH" == Ch11 ]]; then
      stage EXTENDED_CH11_BRIDGE
      start localization_bridge ros2 run ros_gz_bridge parameter_bridge \
        --ros-args -p config_file:="$WS/src/$PKG/config/ros_gz_bridge.yaml"
      stage EXTENDED_CH11_ODOMETRY_ADAPTER
      start simulation_odometry ros2 run my_quadruped_bot sim_odometry
      stage EXTENDED_CH11_MEASURED_ODOM_PAIR
      timeout --signal=TERM --kill-after=4s 24s \
        python3 /work/ci/docker/verify_extended.py ch11 "$OUT/extended.json" \
        2>&1 | tee "$OUT/extended.log"
      grep -q 'BOOK_EXTENDED_CH11_PASS' "$OUT/extended.log"
    else
      echo "Unsupported BOOK_EXTENDED chapter $CH" >&2
      exit 2
    fi
    stage EXTENDED_BOUNDARY_PASS
    echo "$CH:EXTENDED_BOUNDARY_PASS_NOT_WHOLE_CHAPTER" | tee "$OUT/verdict.txt"
    exit 0
  fi
  if [[ "${BOOK_DYNAMIC:-0}" == "1" ]]; then
    if [[ "$CH" == "Ch09" ]]; then
      stage DYNAMIC_CH09_BRIDGE
      start joint_bridge ros2 run ros_gz_bridge parameter_bridge \
        --ros-args -p config_file:="$WS/src/$PKG/config/ros_gz_bridge.yaml"
      stage DYNAMIC_CH09_SINGLE_LEG
      start single_leg ros2 run my_quadruped_bot single_leg_mover
      timeout --signal=TERM --kill-after=4s 24s \
        python3 /work/ci/docker/verify_dynamic.py ch09 "$OUT/dynamic.json" \
        2>&1 | tee "$OUT/dynamic.log"
    elif [[ "$CH" == "Ch10" ]]; then
      stage DYNAMIC_CH10_IK_GEOMETRY
      timeout 20s python3 /work/ci/docker/ch10_ik_boundary.py \
        "$WS/src/$PKG" "$OUT/ik_boundary.json" \
        2>&1 | tee "$OUT/dynamic.log"
    else
      stage DYNAMIC_CH11_SENSOR_BRIDGE
      start sensor_bridge ros2 run ros_gz_bridge parameter_bridge \
        --ros-args -p config_file:="$WS/src/$PKG/config/ros_gz_bridge.yaml"
      timeout --signal=TERM --kill-after=4s 32s \
        python3 /work/ci/docker/verify_dynamic.py ch11 "$OUT/dynamic.json" \
        2>&1 | tee "$OUT/dynamic.log"
    fi
    stage DYNAMIC_PASS
    echo "$CH:DYNAMIC_BOUNDARY_PASS_GAIT_SLAM_FULL_NOT_RUN" | tee "$OUT/verdict.txt"
    exit 0
  fi
  stage WORLD_SPAWN_CLOCK_PASS
  echo "$CH:WORLD_SPAWN_CLOCK_PASS_GAIT_SLAM_NOT_RUN" | tee "$OUT/verdict.txt"
  exit 0
fi

stage CONTROLLER_MANAGER
ready_manager
stage CONTROLLER_SPAWN
timeout --signal=TERM --kill-after=5s 50s ros2 run controller_manager spawner joint_state_broadcaster --controller-manager /controller_manager --controller-manager-timeout 35 2>&1 | tee "$OUT/jsb.log"
timeout --signal=TERM --kill-after=5s 50s ros2 run controller_manager spawner arm_controller --controller-manager /controller_manager --controller-manager-timeout 35 2>&1 | tee "$OUT/arm.log"
stage CONTROLLER_BOTH_ACTIVE
timeout 12s ros2 control list_controllers -c /controller_manager | tee "$OUT/controllers.txt"
grep -E 'joint_state_broadcaster.*active' "$OUT/controllers.txt"
grep -E 'arm_controller.*active' "$OUT/controllers.txt"
timeout 12s ros2 topic info -v /arm_controller/joint_trajectory > "$OUT/trajectory_topic.txt"
grep -Eq 'Subscription count: [1-9]' "$OUT/trajectory_topic.txt"
stage REAL_GUIDE_TRAJECTORY
start simple_controller ros2 run manipulation_basics simple_controller
timeout --signal=TERM --kill-after=5s 35s python3 /work/ci/docker/verify_ch05_motion.py "$OUT/motion.json" 2>&1 | tee "$OUT/motion.log"
grep -q 'CH05_MEASURED_MOTION_PASS' "$OUT/motion.log"
if [[ "${BOOK_DYNAMIC:-0}" == "1" ]]; then
  stage DYNAMIC_CH05_TRACKING_ERROR
  timeout --signal=TERM --kill-after=4s 22s \
    python3 /work/ci/docker/verify_dynamic.py ch05 "$OUT/dynamic.json" \
    2>&1 | tee "$OUT/dynamic.log"
fi
stage CH05_PASS
echo 'CH05_ACTIVE_TRAJECTORY_AND_FEEDBACK_PASS_GUI_NOT_RUN' | tee "$OUT/verdict.txt"
