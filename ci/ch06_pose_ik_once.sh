#!/usr/bin/env bash
# Issue #134 only: reuse #133 immutable GHCR image, packages, model check and mock launch.
# SIMULATION ONLY. Never rerun accepted named-ready here.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch06-pose-ik"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=64 ROS_LOCALHOST_ONLY=1 DEBIAN_FRONTEND=noninteractive
echo "source_sha=${RUN_SOURCE_SHA:-UNKNOWN}" > "$OUT/environment.txt"
echo "base_digest=sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f" >> "$OUT/environment.txt"
STAGE=INIT
LAUNCH_PID=
stage() { STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
cleanup() {
  rc="$?"; trap - EXIT; set +e
  verdict=NOT_STARTED
  if [[ -n "$LAUNCH_PID" ]]; then
    kill -TERM "$LAUNCH_PID" 2>/dev/null || true
    verdict=SIGTERM_REQUESTED
    for i in $(seq 1 30); do
      if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then verdict=ROS_LAUNCH_EXITED_AFTER_SIGTERM; break; fi
      sleep 0.2
    done
    if [[ "$verdict" == SIGTERM_REQUESTED ]]; then
      kill -KILL "$LAUNCH_PID" 2>/dev/null || true
      verdict=ROS_LAUNCH_REQUIRED_SIGKILL
      if [[ "$rc" -eq 0 ]]; then rc=75; fi
    fi
    wait "$LAUNCH_PID" 2>/dev/null || true
  fi
  printf '{"status":"%s","exit_code":%d,"stage":"%s","shutdown":"%s","named_ready_retest":"NOT_RUN","gazebo":"NOT_RUN"}\n' \
    "$([[ "$rc" -eq 0 ]] && echo SCOPED_PASS || echo FAIL)" "$rc" "$STAGE" "$verdict" > "$OUT/result.json"
  echo "CH06_POSE_SHUTDOWN=$verdict" | tee -a "$OUT/stages.log"
  exit "$rc"
}
trap cleanup EXIT
stage REUSE_MOVEIT_DEPENDENCIES
packages=(
  ros-jazzy-moveit-py ros-jazzy-moveit-configs-utils
  ros-jazzy-moveit-planners-ompl ros-jazzy-moveit-simple-controller-manager
  ros-jazzy-moveit-kinematics ros-jazzy-controller-manager ros-jazzy-ros2controlcli
  ros-jazzy-joint-trajectory-controller ros-jazzy-joint-state-broadcaster
  ros-jazzy-ros2-control ros-jazzy-robot-state-publisher ros-jazzy-xacro
)
timeout --signal=TERM --kill-after=10s 110s apt-get update -qq > "$OUT/apt_update.log" 2>&1
timeout --signal=TERM --kill-after=15s 235s apt-get install -y --no-install-recommends "${packages[@]}" > "$OUT/apt_install.log" 2>&1
dpkg-query -W "${packages[@]}" > "$OUT/installed_versions.txt"
set +u; source /opt/ros/jazzy/setup.bash; set -u
stage BUILD_SAME_CH06_MODEL
cd "$ROOT/Ch06/ros2_ws"
timeout --signal=TERM --kill-after=10s 125s colcon build --symlink-install \
  --packages-select my_robot_description my_robot_moveit_config my_robot_control \
  > "$OUT/colcon.log" 2>&1
set +u; source "$PWD/install/setup.bash"; set -u
python3 "$ROOT/ci/ch06_verify_installed_model.py" "$OUT/model_contract.json" > "$OUT/model_check.log" 2>&1
grep -q CH06_MODEL_CONTRACT_PASS "$OUT/model_check.log"
ros2 pkg executables my_robot_control > "$OUT/executables.txt"
grep -q 'my_robot_control pose_ik_node' "$OUT/executables.txt"
stage REUSE_FAKE_HARDWARE
ros2 launch my_robot_moveit_config moveit_64_headless.launch.py > "$OUT/launch.log" 2>&1 &
LAUNCH_PID=$!
READY=0
for i in $(seq 1 36); do
  kill -0 "$LAUNCH_PID" 2>/dev/null || break
  if timeout 5s ros2 control list_controllers -c /controller_manager > "$OUT/controllers.txt" 2>&1; then
    if grep -q 'arm_group_controller.*active' "$OUT/controllers.txt" \
       && grep -q 'joint_state_broadcaster.*active' "$OUT/controllers.txt"; then READY=1; break; fi
  fi
  sleep 0.6
done
[[ "$READY" == 1 ]] || { echo CH06_POSE_CONTROLLERS_BLOCKED; exit 4; }
timeout 10s ros2 control list_hardware_components -c /controller_manager > "$OUT/hardware.txt" 2>&1
grep -q FakeSystem "$OUT/hardware.txt" || { echo CH06_POSE_NOT_FAKE_HARDWARE; exit 5; }
timeout 10s ros2 action list -t > "$OUT/actions.txt"
grep -Fq '/arm_group_controller/follow_joint_trajectory [control_msgs/action/FollowJointTrajectory]' "$OUT/actions.txt"
timeout 8s ros2 topic echo /joint_states --once > "$OUT/joint_states.txt" 2>&1
stage EXECUTE_POSE_ONLY
export CH06_CI_MOCK_CONTROLLER_VERIFIED=1
export CH06_CI_RESULT_RECEIPT="$OUT/pose_receipt.json"
timeout --signal=TERM --kill-after=10s 135s ros2 run my_robot_control pose_ik_node \
  --ci-mock-verified-exit 2>&1 | tee "$OUT/pose_ik.log"
for marker in CH06_POSE_FK_TARGET_CREATED CH06_POSE_IK_GOAL_ACCEPTED \
  CH06_POSE_IK_PLANNING_PASS CH06_POSE_IK_EXECUTION_STATUS=SUCCEEDED \
  CH06_POSE_IK_EXECUTION_FK_FEEDBACK_PASS CH06_POSE_UPSTREAM_3721_TEARDOWN_BYPASSED_AFTER_FK_PASS
do grep -q "$marker" "$OUT/pose_ik.log"; done
stage INDEPENDENT_POSE_RECEIPT_VERIFICATION
python3 - "$CH06_CI_RESULT_RECEIPT" <<'PY'
import json, math, sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
assert d["scenario"] == "fk_derived_pose_ik_mock_only"
assert d["pose_ik"] == d["observed_fk"] == d["planning"] == "PASS"
assert d["execution"] == "SUCCEEDED"
assert d["frame"] == "world" and d["tip"] == "link_wrist"
assert len(d["measured_joint_positions"]) == len(d["fk_seed_joint_positions"]) == 5
assert d["initial_target_translation_m"] >= 0.08
assert d["joint_movement_rad"] >= 0.10
assert math.isfinite(d["position_error_m"]) and d["position_error_m"] <= 0.03
assert math.isfinite(d["orientation_error_rad"]) and d["orientation_error_rad"] <= 0.10
assert d["named_ready_retest"].startswith("NOT_RUN")
assert d["normal_moveitcpp_destructor"] == "NOT_RUN_UPSTREAM_MOVEIT2_3721"
assert d["gazebo_physics"] == d["rviz_gui"] == d["real_hardware"] == "NOT_RUN"
print("CH06_POSE_INDEPENDENT_RECEIPT_PASS")
PY
stage POSE_IK_SCOPED_PASS
echo "CH06_POSE_IK_FK_PLAN_ACTION_OBSERVED_FEEDBACK_PASS_MOCK_ONLY" | tee "$OUT/verdict.txt"
