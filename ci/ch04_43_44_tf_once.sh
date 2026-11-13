#!/usr/bin/env bash
# Ch04 4.3-4.4 actual ROS TF. Ch10 HOLD. No Gazebo.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch04-43-44"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=44 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST PYTHONUNBUFFERED=1
BROADCAST_PID= LISTEN_PID= STAGE=INIT
stage(){ STAGE="$1"; echo "STAGE=$1" | tee -a "$OUT/stages.log"; }
stop_group(){
 local pid="$1" label="$2"
 [[ -n "$pid" ]] || return 0
 kill -INT -- "-$pid" 2>/dev/null || true
 local state=""
 for i in $(seq 1 30); do
   state="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
   [[ -z "$state" || "$state" == Z* ]] && break
   sleep .1
 done
 if [[ -n "$state" && "$state" != Z* ]]; then
   kill -TERM -- "-$pid" 2>/dev/null || true
   echo "${label}_SIGTERM_ESCALATION" | tee -a "$OUT/stages.log"
   for i in $(seq 1 20); do
     state="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
     [[ -z "$state" || "$state" == Z* ]] && break
     sleep .1
   done
   if [[ -n "$state" && "$state" != Z* ]]; then
     kill -KILL -- "-$pid" 2>/dev/null || true
     echo "${label}_SIGKILL_ESCALATION" | tee -a "$OUT/stages.log"
   fi
   wait "$pid" 2>/dev/null || true
   return 1
 fi
 local rc=0
 wait "$pid" || rc=$?
 echo "${label}_SIGINT_SHUTDOWN_RC=$rc" | tee -a "$OUT/stages.log"
 [[ "$rc" == 0 ]]
}
cleanup(){
 rc="$?";trap - EXIT;set +e
 if [[ -n "$LISTEN_PID" ]]; then
   stop_group "$LISTEN_PID" LISTENER
   [[ $? -eq 0 ]] || rc=75
 fi
 if [[ -n "$BROADCAST_PID" ]]; then
   stop_group "$BROADCAST_PID" BROADCASTER
   [[ $? -eq 0 ]] || rc=75
 fi
 printf '{"chapter":"Ch04","sections":["4.3","4.4"],"exit_code":%d,"last_stage":"%s","status":"%s","gazebo":"NOT_RUN","ch10":"HOLD"}\n' \
 "$rc" "$STAGE" "$([[ $rc -eq 0 ]] && echo SCOPED_PASS || echo FAIL)" > "$OUT/result.json"
 exit "$rc"
}
trap cleanup EXIT
stage BUILD_ORIGINAL_MY_ROBOT_TF
cd "$ROOT/Ch04/ros2_ws"
timeout --signal=TERM --kill-after=5s 90s \
  colcon build --symlink-install --packages-select my_robot_tf \
  > "$OUT/colcon.log" 2>&1
set +u; source install/setup.bash; set -u
ros2 pkg executables my_robot_tf > "$OUT/executables.txt"
grep -q 'my_robot_tf dynamic_tf_broadcaster' "$OUT/executables.txt"
grep -q 'my_robot_tf tf_listener' "$OUT/executables.txt"
stage START_ORIGINAL_BROADCASTER_AND_LISTENER
setsid ros2 run my_robot_tf dynamic_tf_broadcaster > "$OUT/broadcaster.log" 2>&1 &
BROADCAST_PID=$!
sleep .6
setsid ros2 run my_robot_tf tf_listener > "$OUT/listener.log" 2>&1 &
LISTEN_PID=$!
stage INDEPENDENT_LIVE_TF_GEOMETRY
timeout --signal=TERM --kill-after=5s 18s \
  python3 "$ROOT/ci/ch04_43_44_tf_probe.py" "$OUT/transform_receipt.json" \
  2>&1 | tee "$OUT/observer.log"
grep -q CH04_43_REAL_2M_CIRCULAR_TF_AND_TANGENT_YAW_PASS "$OUT/observer.log"
stage ACTUAL_ORIGINAL_LISTENER_LOG_PROOF
cat "$OUT/listener.log"
python3 - "$OUT/listener.log" "$OUT/listener_receipt.json" <<'PY'
import json,re,sys
from pathlib import Path
log=Path(sys.argv[1]).read_text(errors="replace")
hits=[float(v) for v in re.findall(
    r"Detected: Turtle is at \([^)]+\), Distance: ([\d.]+)m",log
)]
if len(hits)<3 or not all(abs(x-2.)<.025 for x in hits):
    raise RuntimeError(f"CH04_44_ORIGINAL_LISTENER_DID_NOT_TRACK_DISTANCE count={len(hits)} values={hits}")
Path(sys.argv[2]).write_text(json.dumps({
 "chapter":"Ch04","section":"4.4","status":"SCOPED_PASS",
 "log_distance_samples_m":hits,"target_radius_m":2.0,
 "actual_tf2_buffer_lookup":"PASS",
 "police_bot_additional_frame":"NOT_RUN","rviz_gui":"NOT_RUN"
},indent=2)+"\n")
print(f"CH04_44_ORIGINAL_TF_LISTENER_REAL_LOOKUP_DISTANCE_PASS count={len(hits)}",flush=True)
PY
stage ORIGINAL_ROS_NODES_CTRL_C_SHUTDOWN
stop_group "$LISTEN_PID" LISTENER
LISTEN_PID=
stop_group "$BROADCAST_PID" BROADCASTER
BROADCAST_PID=
sleep .5
ros2 node list > "$OUT/nodes_after.txt"
! grep -Eq '^/(tf_listener_node|dynamic_tf_broadcaster_node)$' "$OUT/nodes_after.txt"
echo CH04_43_44_ACTUAL_ROS_DYNAMIC_TF_LISTENER_CLEAN_EXIT_SCOPED_PASS \
  | tee "$OUT/verdict.txt"
