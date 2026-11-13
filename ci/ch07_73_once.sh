#!/usr/bin/env bash
# Ch07 §7.3 independently observed ROS Image input/output, no Gazebo camera.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch07-73"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=73 ROS_LOCALHOST_ONLY=1 DEBIAN_FRONTEND=noninteractive
echo "source_sha=${RUN_SOURCE_SHA:-UNKNOWN}" > "$OUT/environment.txt"
echo "base=ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f" >> "$OUT/environment.txt"
NODE_PID=
STAGE=INIT
stage(){ STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
cleanup(){
  code="$?"; trap - EXIT; set +e
  shutdown=NOT_STARTED
  if [[ -n "$NODE_PID" ]]; then
    kill -TERM "$NODE_PID" 2>/dev/null || true
    shutdown=SIGTERM_REQUESTED
    for i in $(seq 1 25); do
      if ! kill -0 "$NODE_PID" 2>/dev/null; then
        shutdown=VISION_NODE_EXITED_AFTER_SIGTERM; break
      fi
      sleep 0.2
    done
    if [[ "$shutdown" == SIGTERM_REQUESTED ]]; then
      shutdown=VISION_NODE_REQUIRED_SIGKILL
      kill -KILL "$NODE_PID" 2>/dev/null || true
      if [[ "$code" -eq 0 ]]; then code=75; fi
    fi
    wait "$NODE_PID" 2>/dev/null || true
  fi
  printf '{"status":"%s","exit_code":%d,"stage":"%s","shutdown":"%s","ch07_gazebo_camera":"BLOCKED_ISSUE_127","real_depth":"NOT_RUN","opencv_gui":"NOT_RUN","ch10":"HOLD"}\n' \
    "$([[ "$code" -eq 0 ]] && echo SCOPED_PASS || echo FAIL)" \
    "$code" "$STAGE" "$shutdown" > "$OUT/result.json"
  echo "CH07_73_SHUTDOWN=$shutdown" | tee -a "$OUT/stages.log"
  exit "$code"
}
trap cleanup EXIT
stage CV_BRIDGE_DEPENDENCY_ADDONS
packages=(ros-jazzy-cv-bridge python3-opencv python3-numpy)
timeout --signal=TERM --kill-after=10s 105s apt-get update -qq > "$OUT/apt_update.log" 2>&1
timeout --signal=TERM --kill-after=10s 115s apt-get install -y --no-install-recommends "${packages[@]}" > "$OUT/apt_install.log" 2>&1
dpkg-query -W "${packages[@]}" > "$OUT/versions.txt"
set +u; source /opt/ros/jazzy/setup.bash; set -u
stage CH07_ONLY_BUILD
cd "$ROOT/Ch07/ros2_ws"
timeout --signal=TERM --kill-after=10s 100s colcon build --symlink-install --packages-select vision_basics > "$OUT/colcon.log" 2>&1
set +u; source "$PWD/install/setup.bash"; set -u
ros2 pkg executables vision_basics > "$OUT/executables.txt"
grep -q 'vision_basics vision_processor' "$OUT/executables.txt"
python3 -m py_compile src/vision_basics/vision_basics/vision_processor.py
stage RUN_ACTUAL_VISION_PROCESSOR_NO_GUI
ros2 run vision_basics vision_processor --ros-args -p show_gui:=false > "$OUT/vision_processor.log" 2>&1 &
NODE_PID=$!
stage SEND_ACTUAL_ROS_IMAGES_AND_VERIFY_PROCESSED_TOPIC
export CH07_73_RECEIPT="$OUT/synthetic_ros_image_receipt.json"
timeout --signal=TERM --kill-after=10s 34s python3 "$ROOT/ci/ch07_73_image_roundtrip.py" \
  2>&1 | tee "$OUT/roundtrip.log"
grep -q CH07_73_ACTUAL_ROS_IMAGE_CVBRIDGE_CANNY_MONO8_AND_STAMP_PASS "$OUT/roundtrip.log"
stage INDEPENDENT_RECEIPT_CHECK
python3 - "$CH07_73_RECEIPT" <<'PY'
import json,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
assert d["scenario"]=="synthetic_ROS_image_cv_bridge_OpenCV_Canny_mono8"
assert d["status"]=="SCOPED_PASS"
assert d["input_encoding"]=="bgr8" and d["output_encoding"]=="mono8"
assert d["real_processed_messages_verified"]>=3
assert d["exact_pixels_matched"] and d["exact_header_stamp_preserved"]
assert d["edge_nonzero_pixels"]>0
assert d["actual_gazebo_camera"]=="BLOCKED_ISSUE_127"
assert d["real_depth"]==d["opencv_gui"]==d["real_hardware"]=="NOT_RUN"
assert d["ch10"]=="HOLD"
print("CH07_73_INDEPENDENT_ROS_IMAGE_RECEIPT_PASS")
PY
stage CH07_73_SCOPED_PASS
echo "CH07_73_ROS_CV_BRIDGE_REAL_TOPIC_SCOPED_PASS_GAZEBO_CAMERA_BLOCKED" | tee "$OUT/verdict.txt"
