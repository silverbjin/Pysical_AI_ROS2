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
check_urdf "$OUT/robot.urdf" > "$OUT/urdf.txt"
if [[ "$CH" == Ch05 ]]; then
  python3 /work/ci/docker/verify_urdf_joints.py "$OUT/robot.urdf" joint1 joint2 joint3 joint4 | tee "$OUT/joint_contract.txt"
  WORLD=empty
  SOURCE_WORLD=empty.sdf
  ROBOT=physical_ai_robot
  SPAWN_Z=0.05
else
  python3 /work/ci/docker/verify_urdf_joints.py "$OUT/robot.urdf" fr_hip_joint fr_thigh_joint fr_calf_joint fl_hip_joint fl_thigh_joint fl_calf_joint rr_hip_joint rr_thigh_joint rr_calf_joint rl_hip_joint rl_thigh_joint rl_calf_joint | tee "$OUT/joint_contract.txt"
  WORLD=my_empty_world
  SOURCE_WORLD="$WS/src/$PKG/worlds/empty_world.sdf"
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
stage CH05_PASS
echo 'CH05_ACTIVE_TRAJECTORY_AND_FEEDBACK_PASS_GUI_NOT_RUN' | tee "$OUT/verdict.txt"
