#!/usr/bin/env bash
# SIMULATION ONLY: MoveItPy planning + ros2_control GenericSystem execution.
# Not Gazebo physics and not robot hardware.
set -Eeuo pipefail
set +u
source /opt/ros/jazzy/setup.bash
set -u
ROOT=/work
OUT=$ROOT/ci-results/ch06-moveit
mkdir -p "$OUT"
export ROS_DOMAIN_ID=63
export ROS_LOCALHOST_ONLY=1
export DEBIAN_FRONTEND=noninteractive
echo "source_sha=${RUN_SOURCE_SHA:-UNKNOWN}" > "$OUT/environment.txt"
echo "runtime_base=ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f" >> "$OUT/environment.txt"
STAGE=INIT
LAUNCH_PID=
stage() { STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
cleanup() {
  code="$?"
  trap - EXIT
  set +e
  printf '{"status":"%s","exit_code":%d,"last_stage":"%s","full_chapter_pass":false}\n' \
    "$([[ "$code" -eq 0 ]] && echo "SCOPED_PASS" || echo "FAIL")" \
    "$code" "$STAGE" > "$OUT/result.json"
  if [[ -n "$LAUNCH_PID" ]]; then
    kill -INT "$LAUNCH_PID" 2>/dev/null || true
    for i in $(seq 1 12); do
      if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
        wait "$LAUNCH_PID" 2>/dev/null || true
        exit "$code"
      fi
      sleep 0.3
    done
    echo "SHUTDOWN_ESCALATED_TERM" | tee -a "$OUT/stages.log"
    kill -TERM "$LAUNCH_PID" 2>/dev/null || true
    sleep 1
    if kill -0 "$LAUNCH_PID" 2>/dev/null; then
      echo "SHUTDOWN_ESCALATED_KILL" | tee -a "$OUT/stages.log"
      kill -KILL "$LAUNCH_PID" 2>/dev/null || true
    fi
    wait "$LAUNCH_PID" 2>/dev/null || true
  fi
  exit "$code"
}
trap cleanup EXIT
stage MOVEIT_DEPENDENCY_DISCOVERY
packages=(
  ros-jazzy-moveit-py
  ros-jazzy-moveit-configs-utils
  ros-jazzy-moveit-planners-ompl
  ros-jazzy-moveit-simple-controller-manager
  ros-jazzy-moveit-kinematics
  ros-jazzy-controller-manager
  ros-jazzy-ros2controlcli
  ros-jazzy-joint-trajectory-controller
  ros-jazzy-joint-state-broadcaster
  ros-jazzy-ros2-control
  ros-jazzy-robot-state-publisher
  ros-jazzy-xacro
)
timeout --signal=TERM --kill-after=10s 110s apt-get update -qq \
  > "$OUT/apt_update.log" 2>&1
for pkg in "${packages[@]}"; do
  apt-cache show "$pkg" >/dev/null || { echo "MISSING_APT_PACKAGE=$pkg" | tee -a "$OUT/stages.log"; exit 3; }
done
stage INSTALL_EXACT_RUNTIME_PACKAGES
timeout --signal=TERM --kill-after=15s 235s \
  apt-get install -y --no-install-recommends "${packages[@]}" \
  > "$OUT/apt_install.log" 2>&1
dpkg-query -W "${packages[@]}" > "$OUT/installed_versions.txt"
set +u
source /opt/ros/jazzy/setup.bash
set -u
stage MOVEITPY_IMPORT
python3 - <<'PY'
from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder
print("CH06_MOVEITPY_REAL_IMPORT_PASS")
PY
WS=$ROOT/Ch06/ros2_ws
stage COLCON_BUILD_CH06
cd "$WS"
timeout --signal=TERM --kill-after=10s 125s \
  colcon build --symlink-install --packages-select \
    my_robot_description my_robot_moveit_config my_robot_control \
  2>&1 | tee "$OUT/colcon.log"
set +u
source "$WS/install/setup.bash"
set -u
stage INSTALLED_MODEL_AND_SRDF_CONTRACT
python3 "$ROOT/ci/ch06_verify_installed_model.py" "$OUT/model_contract.json" \
  2>&1 | tee "$OUT/model_check.log"
grep -q CH06_MODEL_CONTRACT_PASS "$OUT/model_check.log"
ros2 pkg executables my_robot_control | tee "$OUT/executables.txt"
grep -q 'my_robot_control hello_node' "$OUT/executables.txt"
stage ROS2_CONTROL_HEADLESS_LAUNCH
ros2 launch my_robot_moveit_config moveit_64_headless.launch.py \
  > "$OUT/launch.log" 2>&1 &
LAUNCH_PID=$!
READY=0
for i in $(seq 1 36); do
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "CH06_HEADLESS_LAUNCH_EXITED_EARLY" | tee -a "$OUT/stages.log"
    break
  fi
  if timeout 5s ros2 control list_controllers -c /controller_manager \
     > "$OUT/controller_status.txt" 2>&1; then
    if grep -E 'arm_group_controller.*active' "$OUT/controller_status.txt" \
        && grep -E 'joint_state_broadcaster.*active' "$OUT/controller_status.txt"; then
      READY=1
      break
    fi
  fi
  sleep 0.6
done
[[ "$READY" == 1 ]] || { echo "CH06_CONTROLLER_NOT_READY"; exit 4; }
stage REAL_ACTION_SERVER
timeout 10s ros2 action list -t > "$OUT/actions.txt"
grep -Fq '/arm_group_controller/follow_joint_trajectory [control_msgs/action/FollowJointTrajectory]' \
  "$OUT/actions.txt" || { echo "CH06_FOLLOW_JOINT_TRAJECTORY_ACTION_MISSING"; exit 5; }
stage REAL_JOINT_STATE_TIMESTAMPS_QOS
timeout 8s ros2 topic echo /joint_states --once \
  > "$OUT/joint_state_sample.txt" 2>&1
timeout 8s ros2 topic info -v /joint_states \
  > "$OUT/joint_state_qos.txt" 2>&1
stage REAL_MOVEITPY_NAMED_READY_PLAN_AND_EXECUTE
timeout --signal=TERM --kill-after=10s 105s \
  ros2 run my_robot_control hello_node --mode named \
  2>&1 | tee "$OUT/hello_moveit.log"
grep -q CH06_NAMED_READY_PLANNING_PASS "$OUT/hello_moveit.log"
grep -q CH06_MOVEIT_EXECUTION_STATUS=SUCCEEDED "$OUT/hello_moveit.log"
grep -q CH06_NAMED_READY_EXECUTION_AND_JOINT_GOAL_PASS "$OUT/hello_moveit.log"
stage NAMED_READY_SCOPED_PASS
echo "CH06_MOVEITPY_PLAN_EXECUTE_JOINT_FEEDBACK_PASS_POSE_IK_NOT_RUN" \
  | tee "$OUT/verdict.txt"
