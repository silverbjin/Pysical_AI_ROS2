#!/usr/bin/env bash
# Ch07 §7.5: measured ROS K + synthetic aligned depth + static TF only.
# No Gazebo RGB-D, no robot commands, no 7.3/7.4 reruns, Ch10 HOLD.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work; OUT="$ROOT/ci-results/ch07-75"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=75 ROS_LOCALHOST_ONLY=1 DEBIAN_FRONTEND=noninteractive
printf 'source_sha=%s\nimage=%s\n' "${RUN_SOURCE_SHA:-UNKNOWN}" \
 'ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f' > "$OUT/environment.txt"
NODE_PID=; TF_PID=; STAGE=INIT
stage(){ STAGE="$1"; echo "STAGE=$STAGE" | tee -a "$OUT/stages.log"; }
cleanup(){
  code="$?"; trap - EXIT; set +e
  shutdown=SIGTERM_CLEAN
  for pid in "$NODE_PID" "$TF_PID"; do
    [[ -n "$pid" ]] || continue
    kill -TERM "$pid" 2>/dev/null || true
    for i in $(seq 1 20); do
      if ! kill -0 "$pid" 2>/dev/null; then break; fi
      sleep 0.2
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
      shutdown=SIGKILL_REQUIRED
      if [[ "$code" -eq 0 ]]; then code=75; fi
    fi
    wait "$pid" 2>/dev/null || true
  done
  printf '{"scope":"synthetic_depth_projection_only","status":"%s","rc":%d,"stage":"%s","shutdown":"%s","rgbd_camera":"BLOCKED_127","ch10":"HOLD"}\n' \
   "$([[ "$code" -eq 0 ]] && echo SCOPED_PASS || echo FAIL)" "$code" "$STAGE" "$shutdown" > "$OUT/result.json"
  echo "CH07_75_SHUTDOWN=$shutdown" | tee -a "$OUT/stages.log"
  exit "$code"
}
trap cleanup EXIT
stage CHECK_FIXED_JAZZY_TF_DEPENDENCY
if ! ros2 pkg prefix tf2_ros > "$OUT/tf2_prefix.txt" 2>&1; then
  timeout --signal=TERM --kill-after=10s 100s apt-get update -qq > "$OUT/apt_update.log" 2>&1
  timeout --signal=TERM --kill-after=10s 120s apt-get install -y --no-install-recommends ros-jazzy-tf2-ros > "$OUT/apt_install.log" 2>&1
fi
dpkg-query -W ros-jazzy-tf2-ros > "$OUT/installed_versions.txt"
stage BUILD_CH07_ONE_PACKAGE
cd "$ROOT/Ch07/ros2_ws"
timeout --signal=TERM --kill-after=10s 95s colcon build --symlink-install --packages-select vision_basics > "$OUT/colcon.log" 2>&1
set +u; source "$PWD/install/setup.bash"; set -u
ros2 pkg executables vision_basics > "$OUT/executables.txt"
grep -q 'vision_basics coord_transformer' "$OUT/executables.txt"
python3 -m py_compile src/vision_basics/vision_basics/coord_transformer.py
stage START_SYNTHETIC_STATIC_OPTICAL_TF
ros2 run tf2_ros static_transform_publisher \
 --x 0.2 --y 0.1 --z 0.4 --roll 0 --pitch 0 --yaw 0 \
 --frame-id base_link --child-frame-id camera_optical_frame \
 > "$OUT/static_tf.log" 2>&1 &
TF_PID="$!"
stage START_REAL_COORD_TRANSFORMER_ROS_NODE
ros2 run vision_basics coord_transformer > "$OUT/transformer.log" 2>&1 &
NODE_PID="$!"
stage REAL_ROS_PROJECT_TWO_DEPTH_FORMATS_AND_INVALID_INPUTS
export CH07_75_RECEIPT="$OUT/depth_projection_receipt.json"
timeout --signal=TERM --kill-after=10s 90s \
  python3 "$ROOT/ci/ch07_75_depth_projection_probe.py" \
  2>&1 | tee "$OUT/probe.log"
for marker in CH07_75_VALID_32FC1_PASS CH07_75_VALID_16UC1_PASS \
  CH07_75_INVALID_DEPTH_NAN_FAIL_CLOSED_PASS \
  CH07_75_INVALID_DEPTH_ZERO_FAIL_CLOSED_PASS \
  CH07_75_INVALID_CAMERA_K_FAIL_CLOSED_PASS \
  CH07_75_INVALID_STALE_STAMP_FAIL_CLOSED_PASS \
  CH07_75_INVALID_MISALIGNED_STAMP_FAIL_CLOSED_PASS \
  CH07_75_INVALID_OPTICAL_FRAME_FAIL_CLOSED_PASS \
  CH07_75_invalid_validity_FAIL_CLOSED_PASS \
  CH07_75_ACTUAL_ROS_SYNTHETIC_DEPTH_CAMERAINFO_TF_SCOPED_PASS
do grep -q "$marker" "$OUT/probe.log"; done
stage INDEPENDENT_RECEIPT_AUDIT
python3 - "$CH07_75_RECEIPT" <<'PY'
import json, math, sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
assert d['scope']=='synthetic_aligned_depth_k_pointstamp_static_tf_actual_ros'
assert d['status']=='SCOPED_PASS'
assert d['accepted_valid_count']==2 and d['invalid_cases_with_no_3d_publication']==7
assert len(d['results'])==9
assert d['results'][0]['encoding']=='32FC1' and d['results'][1]['encoding']=='16UC1'
assert all(math.isfinite(x['xyz_error_m']) and x['xyz_error_m']<=0.002 for x in d['results'][:2])
assert all(x['invalid_published'] is False for x in d['results'][2:])
assert d['input_pixel_point_z']=='area_px2_not_depth'
assert d['actual_gazebo_rgbd']=='BLOCKED_ISSUE_127'
assert d['actual_depth_alignment']==d['moving_wrist_tf']==d['hardware']=='NOT_RUN'
assert d['ch10']=='HOLD'
print('CH07_75_INDEPENDENT_SYNTHETIC_DEPTH_TF_RECEIPT_PASS')
PY
stage CH07_75_SCOPED_PASS
echo 'CH07_75_SYNTHETIC_ROS_DEPTH_K_TF_VALID_AND_FAIL_CLOSED_PASS_REAL_CAMERA_BLOCKED' | tee "$OUT/verdict.txt"
