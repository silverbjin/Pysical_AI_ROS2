#!/usr/bin/env bash
# Gazebo Harmonic actual physics+ros2_control controller-only proof for Ch06 §6.6.
# Never a physical robot or MoveIt trajectory-planning claim.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch06-moveit-gazebo-66"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=67 ROS_LOCALHOST_ONLY=1
export GZ_PARTITION="ch06_66_moveit_${RUN_SOURCE_SHA:-local}_$$"
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
  printf '{"status":"%s","exit_code":%d,"stage":"%s","shutdown":"%s","moveit_planning":"SCOPED_GAZEBO_ONLY_IF_PASS","gazebo_gui":"NOT_RUN","hardware":"NOT_RUN","ch10":"HOLD"}\n' \
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
stage ACTUAL_MOVEIT_OMPL_PLAN_EXECUTION_TO_GAZEBO
export CH06_66_GAZEBO_VERIFIED=1
export CH06_66_MOVEIT_RECEIPT="$OUT/moveit_gazebo_receipt.json"
timeout --signal=TERM --kill-after=10s 135s \
  python3 "$ROOT/ci/ch06_66_moveit_gazebo_probe.py" \
  2>&1 | tee "$OUT/moveit_gazebo.log"
for marker in CH06_66_GAZEBO_MOVEIT_SAME_URDF_AND_SIM_CLOCK_CONFIG_PASS \
  CH06_NAMED_READY_PLANNING_PASS \
  CH06_MOVEIT_EXECUTION_STATUS=SUCCEEDED \
  CH06_NAMED_READY_EXECUTION_AND_JOINT_GOAL_PASS \
  CH06_66_MOVEIT_OMPL_PLAN_GAZEBO_ACTION_AND_JOINT_FEEDBACK_PASS \
  CH06_66_MOVEIT_TO_GAZEBO_SCOPED_PASS
do grep -q "$marker" "$OUT/moveit_gazebo.log"; done
stage INDEPENDENT_MOVEIT_TO_GAZEBO_PLAN_EXECUTION_RECEIPT
python3 - "$CH06_66_MOVEIT_RECEIPT" <<'PY'
import json, math, sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
assert d["scope"]=="moveitpy_ompl_plan_execute_real_gazebo_gz_ros2_control"
assert d["planning"]=="PASS" and d["execution"]=="SUCCEEDED"
assert d["joint_goal"]=="PASS" and d["use_sim_time"] is True
assert "my_robot.ros2_control_gazebo.urdf.xacro" in d["gazebo_model"]
assert d["controller_only_previous_case"].startswith("NOT_RERUN")
assert len(d["per_joint_error_rad"])==5
assert all(math.isfinite(x) and x <= 0.06 for x in d["per_joint_error_rad"].values())
assert d["max_joint_error_rad"] <= 0.06
assert d["moveitpy_destructor"]=="NOT_RUN_UPSTREAM_MOVEIT2_3721"
assert d["rviz_gui"]==d["real_hardware"]==d["gripper"]=="NOT_RUN"
assert d["ch10"]=="HOLD"
print("CH06_66_INDEPENDENT_MOVEIT_PLAN_TO_REAL_GAZEBO_ACTION_RECEIPT_PASS")
PY
stage MOVEIT_TO_REAL_GAZEBO_SCOPED_PASS_NO_GUI
echo "CH06_66_MOVEIT_OMPL_PLAN_REAL_GAZEBO_CONTROLLER_EXECUTION_SCOPED_PASS" | tee "$OUT/verdict.txt"
