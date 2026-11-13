#!/usr/bin/env bash
# Ch07 §7.4 actual ROS red object detector, synthetic input only.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch07-74"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=74 ROS_LOCALHOST_ONLY=1 DEBIAN_FRONTEND=noninteractive
printf 'source_sha=%s\nbase=%s\n' "${RUN_SOURCE_SHA:-UNKNOWN}" \
 'ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f' > "$OUT/environment.txt"
NODE_PID=
STAGE=INIT
stage(){ STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
cleanup(){
  rc="$?"; trap - EXIT; set +e
  shutdown=NOT_STARTED
  if [[ -n "$NODE_PID" ]]; then
    kill -TERM "$NODE_PID" 2>/dev/null || true
    shutdown=SIGTERM_REQUESTED
    for i in $(seq 1 25); do
      if ! kill -0 "$NODE_PID" 2>/dev/null; then
        shutdown=ROS_DETECTOR_EXITED_AFTER_SIGTERM; break
      fi
      sleep 0.2
    done
    if [[ "$shutdown" == SIGTERM_REQUESTED ]]; then
      kill -KILL "$NODE_PID" 2>/dev/null || true
      shutdown=ROS_DETECTOR_REQUIRED_SIGKILL
      if [[ "$rc" == 0 ]]; then rc=75; fi
    fi
    wait "$NODE_PID" 2>/dev/null || true
  fi
  printf '{"status":"%s","rc":%d,"stage":"%s","shutdown":"%s","actual_gazebo_rgbd":"BLOCKED_127","ch10":"HOLD"}\n' \
    "$([[ "$rc" == 0 ]] && echo SCOPED_PASS || echo FAIL)" "$rc" "$STAGE" "$shutdown" > "$OUT/result.json"
  echo "CH07_74_SHUTDOWN=$shutdown" | tee -a "$OUT/stages.log"
  exit "$rc"
}
trap cleanup EXIT
stage REUSE_BASE_AND_CV_BRIDGE_DEPENDENCIES
packages=(ros-jazzy-cv-bridge python3-opencv python3-numpy)
timeout --signal=TERM --kill-after=10s 105s apt-get update -qq > "$OUT/apt_update.log" 2>&1
timeout --signal=TERM --kill-after=10s 115s apt-get install -y --no-install-recommends "${packages[@]}" > "$OUT/apt_install.log" 2>&1
dpkg-query -W "${packages[@]}" > "$OUT/versions.txt"
set +u; source /opt/ros/jazzy/setup.bash; set -u
stage BUILD_CH07_ONLY
cd "$ROOT/Ch07/ros2_ws"
timeout --signal=TERM --kill-after=10s 100s colcon build --symlink-install --packages-select vision_basics > "$OUT/colcon.log" 2>&1
set +u; source "$PWD/install/setup.bash"; set -u
ros2 pkg executables vision_basics > "$OUT/executables.txt"
grep -q 'vision_basics object_detector' "$OUT/executables.txt"
python3 -m py_compile src/vision_basics/vision_basics/object_detector.py
stage START_ACTUAL_RED_DETECTOR_ROS_NODE
ros2 run vision_basics object_detector --ros-args -p min_area_px2:=500.0 > "$OUT/object_detector.log" 2>&1 &
NODE_PID=$!
stage ONE_TWO_BLANK_ACTUAL_ROS_IMAGE_CASES
export CH07_74_RECEIPT="$OUT/red_detection_receipt.json"
timeout --signal=TERM --kill-after=10s 52s python3 "$ROOT/ci/ch07_74_red_objects_probe.py" \
  2>&1 | tee "$OUT/probe.log"
for marker in CH07_74_CASE_1_RED_VALID_PASS CH07_74_CASE_2_MAX_CONTOUR_PASS \
  CH07_74_CASE_3_EMPTY_INVALIDATION_PASS \
  CH07_74_REAL_ROS_RED_TARGET_AND_INVALIDATION_SCOPED_PASS
do grep -q "$marker" "$OUT/probe.log"; done
stage INDEPENDENT_REDCONTOUR_RECEIPT
python3 - "$CH07_74_RECEIPT" <<'PY'
import json,sys,math
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
assert d["chapter"]=="Ch07" and d["section"]=="7.4"
assert d["status"]=="SCOPED_PASS" and d["threshold_px2"]==500
assert d["one_red"]["status"]=="VALID" and d["two_red_largest"]["status"]=="VALID"
assert abs(d["one_red"]["cx"]-140)<=2 and abs(d["one_red"]["cy"]-110)<=2
assert abs(d["two_red_largest"]["cx"]-225)<=2 and abs(d["two_red_largest"]["cy"]-160)<=2
assert d["one_red"]["area_px2"]>500 and d["two_red_largest"]["area_px2"]>500
assert d["empty"]["status"]=="EMPTY_INVALIDATED" and d["empty"]["target_count"]==0
assert d["point_z_semantics"]=="area_px2_NOT_meters"
assert d["gazebo_camera"]=="BLOCKED_ISSUE_127"
assert d["depth_and_3d"]==d["gui"]==d["hardware"]=="NOT_RUN"
assert d["ch10"]=="HOLD"
print("CH07_74_INDEPENDENT_TARGET_AND_VALIDITY_RECEIPT_PASS")
PY
stage CH07_74_SCOPED_PASS
echo "CH07_74_RED_HSV_LARGEST_CONTOUR_PIXEL_VALIDITY_REAL_ROS_PASS_SYNTHETIC_ONLY" | tee "$OUT/verdict.txt"
