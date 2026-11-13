#!/usr/bin/env bash
# Gazebo Harmonic actual physics+ros2_control controller-only proof for Ch06 §6.6.
# Never a physical robot or MoveIt trajectory-planning claim.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch06-gazebo-66"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=66 ROS_LOCALHOST_ONLY=1
export GZ_PARTITION="ch06_66_${RUN_SOURCE_SHA:-local}_$$"
export DEBIAN_FRONTEND=noninteractive
echo "source_sha=${RUN_SOURCE_SHA:-UNKNOWN}" > "$OUT/environment.txt"
echo "image=ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f" >> "$OUT/environment.txt"
echo "ros_domain=$ROS_DOMAIN_ID" >> "$OUT/environment.txt"
echo "gz_partition=$GZ_PARTITION" >> "$OUT/environment.txt"
LAUNCH_PID=
STAGE=INIT
stage() { STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
cleanup() {
  code="$?"; trap - EXIT; set +e
  shutdown=NOT_STARTED
  if [[ -n "$LAUNCH_PID" ]]; then
    shutdown=SIGTERM_REQUESTED
    kill -TERM "$LAUNCH_PID" 2>/dev/null || true
    for _ in $(seq 1 40); do
      if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
        shutdown=ROS_LAUNCH_EXITED_AFTER_SIGTERM; break
      fi
      sleep 0.2
    done
    if [[ "$shutdown" == SIGTERM_REQUESTED ]]; then
      kill -KILL "$LAUNCH_PID" 2>/dev/null || true
      shutdown=ROS_LAUNCH_REQUIRED_SIGKILL
      if [[ "$code" -eq 0 ]]; then code=75; fi
    fi
    wait "$LAUNCH_PID" 2>/dev/null || true
  fi
  printf '{"status":"%s","exit_code":%d,"stage":"%s","shutdown":"%s","moveit_planning":"NOT_RUN","gazebo_gui":"NOT_RUN","hardware":"NOT_RUN","ch10":"HOLD"}\n' \
    "$([[ "$code" -eq 0 ]] && echo CONTROLLER_SCOPE_PASS || echo FAIL)" \
    "$code" "$STAGE" "$shutdown" > "$OUT/result.json"
  echo "CH06_66_SHUTDOWN=$shutdown" | tee -a "$OUT/stages.log"
  exit "$code"
}
trap cleanup EXIT
stage REUSE_PINNED_IMAGE_AND_MINIMUM_REAL_DEPENDENCIES
packages=(
  ros-jazzy-moveit-py ros-jazzy-moveit-configs-utils
  ros-jazzy-moveit-planners-ompl ros-jazzy-moveit-simple-controller-manager
  ros-jazzy-moveit-kinematics ros-jazzy-moveit-ros-move-group
  ros-jazzy-controller-manager ros-jazzy-ros2controlcli
  ros-jazzy-joint-trajectory-controller ros-jazzy-joint-state-broadcaster
  ros-jazzy-ros2-control ros-jazzy-robot-state-publisher ros-jazzy-xacro
  ros-jazzy-gz-ros2-control
)
timeout --signal=TERM --kill-after=10s 110s apt-get update -qq > "$OUT/apt_update.log" 2>&1
for pkg in "${packages[@]}"; do
  apt-cache show "$pkg" >/dev/null || { echo "CH06_66_APT_MISSING=$pkg"; exit 3; }
done
timeout --signal=TERM --kill-after=15s 235s apt-get install -y --no-install-recommends \
  "${packages[@]}" > "$OUT/apt_install.log" 2>&1
dpkg-query -W "${packages[@]}" > "$OUT/versions.txt"
set +u; source /opt/ros/jazzy/setup.bash; set -u
stage CH06_BUILD_AND_REAL_GAZEBO_URDF_CHECK
cd "$ROOT/Ch06/ros2_ws"
python3 -m py_compile src/my_robot_moveit_config/launch/Gazebo_moveit.launch.py
timeout --signal=TERM --kill-after=10s 130s colcon build --symlink-install \
  --packages-select my_robot_description my_robot_moveit_config my_robot_control \
  > "$OUT/colcon.log" 2>&1
set +u; source "$PWD/install/setup.bash"; set -u
xacro "$(ros2 pkg prefix --share my_robot_description)/urdf/my_robot.ros2_control_gazebo.urdf.xacro" > "$OUT/gazebo_robot.urdf"
grep -q 'gz_ros2_control/GazeboSimSystem' "$OUT/gazebo_robot.urdf"
grep -q 'gz_ros2_control::GazeboSimROS2ControlPlugin' "$OUT/gazebo_robot.urdf"
if grep -q 'mock_components/GenericSystem' "$OUT/gazebo_robot.urdf"; then
  echo "CH06_66_FAKE_COMPONENT_IN_GAZEBO_URDF"; exit 4
fi
stage START_REAL_GAZEBO_HEADLESS_ORIGINAL_LAUNCH
ros2 launch my_robot_moveit_config Gazebo_moveit.launch.py \
  use_sim_time:=true headless:=true start_rviz:=false > "$OUT/launch.log" 2>&1 &
LAUNCH_PID=$!
READY=0
for i in $(seq 1 65); do
  kill -0 "$LAUNCH_PID" 2>/dev/null || break
  if timeout 4s ros2 control list_controllers -c /controller_manager > "$OUT/controllers.txt" 2>&1; then
    if grep -q 'arm_group_controller.*active' "$OUT/controllers.txt" \
       && grep -q 'joint_state_broadcaster.*active' "$OUT/controllers.txt"; then
      READY=1; break
    fi
  fi
  sleep 0.5
done
[[ "$READY" == 1 ]] || {
  echo "CH06_66_GAZEBO_CONTROLLER_NOT_READY"; tail -70 "$OUT/launch.log"; exit 5;
}
stage GAZEBO_PLUGIN_AND_ACTUAL_ACTION_DISCOVERY
grep -q 'Entity creation successful' "$OUT/launch.log" || {
  echo "CH06_66_ENTITY_CREATION_NOT_PROVEN"; exit 6; }
timeout 8s ros2 control list_hardware_components -c /controller_manager > "$OUT/hardware.txt"
grep -q 'GazeboSimSystem' "$OUT/hardware.txt" || {
  echo "CH06_66_GAZEBO_PLUGIN_HARDWARE_NOT_ACTIVE"; exit 7; }
if grep -q FakeSystem "$OUT/hardware.txt"; then echo "CH06_66_FAKE_HARDWARE_FORBIDDEN"; exit 8; fi
timeout 8s ros2 action list -t > "$OUT/actions.txt"
grep -Fq '/arm_group_controller/follow_joint_trajectory [control_msgs/action/FollowJointTrajectory]' "$OUT/actions.txt"
timeout 10s ros2 topic echo /clock --once > "$OUT/clock_sample.txt" 2>&1
timeout 10s ros2 topic echo /joint_states --once > "$OUT/joint_sample.txt" 2>&1
stage ACTUAL_ONE_GAZEBO_CONTROLLER_GOAL
export CH06_66_RECEIPT="$OUT/gazebo_action_receipt.json"
timeout --signal=TERM --kill-after=10s 105s \
  python3 "$ROOT/ci/ch06_66_gazebo_action_probe.py" \
  2>&1 | tee "$OUT/probe.log"
for marker in CH06_66_SIM_CLOCK_AND_JOINT_STREAM_PASS \
  CH06_66_ACTUAL_GAZEBO_ACTION_SERVER_PASS \
  CH06_66_GAZEBO_GOAL_ACCEPTED \
  CH06_66_GAZEBO_FOLLOW_JOINT_TRAJECTORY_SUCCEEDED \
  CH06_66_GAZEBO_JOINT_MOTION_FEEDBACK_PASS \
  CH06_66_CONTROLLER_GAZEBO_SCOPE_PASS_MOVEIT_PLANNING_NOT_RUN
do grep -q "$marker" "$OUT/probe.log"; done
stage INDEPENDENT_GAZEBO_RECEIPT_AUDIT
python3 - "$CH06_66_RECEIPT" <<'PY'
import json, math, sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
assert d["scope"]=="actual_gazebo_gz_ros2_control_one_action_no_moveit_plan"
assert d["action"]=="FollowJointTrajectory"
assert d["goal_status"]==4 and d["error_code"]==0
assert d["observed_joint_movement_rad"] >= 0.20
assert d["target_error_rad"] < 0.08
assert d["clock_advanced_s"] >= 2
assert d["joint_samples"] >= 25 and d["action_feedback_count"] >= 1
assert all(math.isfinite(d[k]) for k in
  ("observed_joint_movement_rad","target_error_rad","clock_advanced_s"))
assert d["moveit_planning"]=="NOT_RUN" and d["gazebo_gui"]=="NOT_RUN"
assert d["real_hardware"]==d["gripper"]=="NOT_RUN" and d["ch10"]=="HOLD"
print("CH06_66_INDEPENDENT_REAL_GAZEBO_CONTROLLER_RECEIPT_PASS")
PY
stage CONTROLLER_PHYSICS_SCOPE_PASS_NOT_MOVEIT_PLANNING
echo "CH06_66_REAL_GAZEBO_CONTROLLER_ACTION_JOINT_FEEDBACK_PASS_MOVEIT_PLANNING_NOT_RUN" | tee "$OUT/verdict.txt"
