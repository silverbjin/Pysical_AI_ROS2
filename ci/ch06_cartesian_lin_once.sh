#!/usr/bin/env bash
# Ch06 §6.5 only — existing immutable Jazzy runtime and mock-only controller.
# No Gazebo, no hardware, no rerun of accepted Ch06 §6.4 tests.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch06-lin-65"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=65 ROS_LOCALHOST_ONLY=1 DEBIAN_FRONTEND=noninteractive
printf 'source_sha=%s\nbase_image=%s\n' "${RUN_SOURCE_SHA:-UNKNOWN}" \
  'ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f' > "$OUT/environment.txt"
STAGE=INIT
LAUNCH_PID=
stage() { STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
cleanup() {
  code="$?"; trap - EXIT; set +e
  shutdown=NOT_STARTED
  if [[ -n "$LAUNCH_PID" ]]; then
    kill -TERM "$LAUNCH_PID" 2>/dev/null || true
    shutdown=SIGTERM_REQUESTED
    for i in $(seq 1 30); do
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
  printf '{"status":"%s","exit_code":%d,"stage":"%s","shutdown":"%s","ch06_64_retest":"NOT_RUN","ch10":"HOLD","gazebo":"NOT_RUN"}\n' \
    "$([[ "$code" -eq 0 ]] && echo SCOPED_PASS || echo FAIL)" \
    "$code" "$STAGE" "$shutdown" > "$OUT/result.json"
  echo "CH06_65_SHUTDOWN=$shutdown" | tee -a "$OUT/stages.log"
  exit "$code"
}
trap cleanup EXIT
stage EXACT_EXISTING_IMAGE_PLUS_PILZ_APT
packages=(
  ros-jazzy-moveit-py ros-jazzy-moveit-configs-utils
  ros-jazzy-moveit-planners-ompl ros-jazzy-moveit-simple-controller-manager
  ros-jazzy-moveit-kinematics ros-jazzy-controller-manager ros-jazzy-ros2controlcli
  ros-jazzy-joint-trajectory-controller ros-jazzy-joint-state-broadcaster
  ros-jazzy-ros2-control ros-jazzy-robot-state-publisher ros-jazzy-xacro
  ros-jazzy-pilz-industrial-motion-planner
)
timeout --signal=TERM --kill-after=10s 110s apt-get update -qq > "$OUT/apt_update.log" 2>&1
for package in "${packages[@]}"; do
  apt-cache show "$package" >/dev/null || { echo "CH06_65_PACKAGE_MISSING=$package"; exit 3; }
done
timeout --signal=TERM --kill-after=15s 235s apt-get install -y --no-install-recommends \
  "${packages[@]}" > "$OUT/apt_install.log" 2>&1
dpkg-query -W "${packages[@]}" > "$OUT/installed_versions.txt"
set +u; source /opt/ros/jazzy/setup.bash; set -u
python3 - <<'PY'
from moveit.planning import PlanRequestParameters
from moveit.core.robot_state import RobotState
print("CH06_65_MOVEITPY_PILZ_API_IMPORT_PASS")
PY
stage BUILD_SAME_CH06_WORKSPACE
cd "$ROOT/Ch06/ros2_ws"
python3 -m py_compile src/my_robot_control/my_robot_control/cartesian_path.py
timeout --signal=TERM --kill-after=10s 125s colcon build --symlink-install \
  --packages-select my_robot_description my_robot_moveit_config my_robot_control \
  > "$OUT/colcon.log" 2>&1
set +u; source "$PWD/install/setup.bash"; set -u
python3 "$ROOT/ci/ch06_verify_installed_model.py" "$OUT/model_contract.json" > "$OUT/model_check.log" 2>&1
grep -q CH06_MODEL_CONTRACT_PASS "$OUT/model_check.log"
ros2 pkg prefix pilz_industrial_motion_planner > "$OUT/pilz_prefix.txt"
stage REUSE_ACTUAL_FAKE_CONTROLLER_LAUNCH
ros2 launch my_robot_moveit_config moveit_64_headless.launch.py > "$OUT/launch.log" 2>&1 &
LAUNCH_PID=$!
READY=0
for i in $(seq 1 36); do
  kill -0 "$LAUNCH_PID" 2>/dev/null || break
  if timeout 5s ros2 control list_controllers -c /controller_manager > "$OUT/controllers.txt" 2>&1; then
    if grep -q 'arm_group_controller.*active' "$OUT/controllers.txt" \
       && grep -q 'joint_state_broadcaster.*active' "$OUT/controllers.txt"; then
      READY=1; break
    fi
  fi
  sleep 0.6
done
[[ "$READY" == 1 ]] || { echo CH06_65_CONTROLLER_BLOCKED; exit 4; }
timeout 10s ros2 control list_hardware_components -c /controller_manager > "$OUT/hardware.txt" 2>&1
grep -q FakeSystem "$OUT/hardware.txt" || { echo CH06_65_REAL_HARDWARE_FORBIDDEN; exit 5; }
timeout 10s ros2 action list -t > "$OUT/actions.txt"
grep -Fq '/arm_group_controller/follow_joint_trajectory [control_msgs/action/FollowJointTrajectory]' "$OUT/actions.txt"
timeout 8s ros2 topic echo /joint_states --once > "$OUT/joint_states.txt" 2>&1
stage ACTUAL_ORIGINAL_BOOK_ENTRYPOINT_4_LIN_LEGS
export CH06_CI_MOCK_CONTROLLER_VERIFIED=1
export CH06_CI_RESULT_RECEIPT="$OUT/cartesian_receipt.json"
timeout --signal=TERM --kill-after=10s 175s \
  python3 -m my_robot_control.cartesian_path --ci-mock-verified-exit \
  2>&1 | tee "$OUT/cartesian.log"
for marker in CH06_65_PILZ_CONFIG_AND_CARTESIAN_LIMITS_PASS \
  CH06_65_PILZ_PTP_PREPOSITION_PLANNING_PASS \
  CH06_65_PTP_POSITIONING_EXECUTION_AND_FK_PASS \
  CH06_65_FOUR_SEGMENT_CLOSED_PATH_PASS \
  CH06_65_PILZ_LIN_FULL_SCOPED_PASS_MOCK_ONLY
do grep -q "$marker" "$OUT/cartesian.log"; done
[[ "$(grep -c CH06_65_LIN_PLANNED_PATH_PASS "$OUT/cartesian.log")" == 4 ]]
[[ "$(grep -c CH06_65_LIN_EXECUTION_AND_MEASURED_PATH_PASS "$OUT/cartesian.log")" == 4 ]]
stage INDEPENDENT_CLOSED_PATH_AND_OBSERVED_FK_AUDIT
python3 - "$CH06_CI_RESULT_RECEIPT" <<'PY'
import json, math, sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
assert d["scenario"] == "four_segment_pilz_lin_xz_mock_controller"
assert d["side_length_m"] == 0.04
assert d["frame"] == "world" and d["tip"] == "link_wrist"
assert d["pilz_ptp_preposition"] == "PASS"
legs=d["pilz_lin_segments"]
assert len(legs)==4 and {a["segment"] for a in legs}==set(range(1,5))
for x in legs:
    assert x["planner"] == "pilz_industrial_motion_planner/LIN"
    assert x["execution"] == "SUCCEEDED"
    assert x["planned_points"] >= 3 and x["measured_samples"] >= 5
    for key,limit in (
        ("planned_max_deviation_m",0.012),
        ("measured_max_deviation_m",0.025),
        ("position_error_m",0.03),
        ("orientation_error_rad",0.10),
    ):
        assert math.isfinite(x[key]) and x[key] <= limit, (x["segment"],key,x[key])
assert math.isfinite(d["closure_position_error_m"]) and d["closure_position_error_m"] <= 0.03
assert d["gazebo_physics"] == d["rviz_gui"] == d["hardware"] == "NOT_RUN"
assert d["ch10"] == "HOLD" and d["other_chapter_retests"] == "NOT_RUN"
print("CH06_65_INDEPENDENT_4_LIN_SEGMENTS_RECEIPT_PASS")
PY
stage CH06_65_SCOPED_PASS
echo "CH06_65_PILZ_LIN_PLAN_EXECUTE_MEASURED_XZ_RECTANGLE_SCOPED_PASS_MOCK_ONLY" | tee "$OUT/verdict.txt"
