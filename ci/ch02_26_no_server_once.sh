#!/usr/bin/env bash
# Ch02 §2.6: REAL CountUntilClient behavior when no ActionServer exists.
# Accepted goal/rejection/cancellation are explicitly not rerun.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT="$PWD"
OUT="$ROOT/ci-results/ch02-26-no-server"
mkdir -p "$OUT"
export ROS_DOMAIN_ID=26
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export PYTHONUNBUFFERED=1
stage(){ echo "STAGE=$1" | tee -a "$OUT/stages.log"; }
stage BUILD_ORIGINAL_BOOK_CH02_ROS_PACKAGES
cd "$ROOT/Ch02/ros2_ws"
timeout --signal=TERM --kill-after=5s 160s \
  colcon build --symlink-install --packages-up-to my_robot_system \
  > "$OUT/build.log" 2>&1
set +u; source install/setup.bash; set -u
ros2 pkg executables my_robot_system | tee "$OUT/executables.txt"
grep -q 'count_until_client' "$OUT/executables.txt"
ros2 interface show my_robot_interfaces/action/CountUntil > "$OUT/interface.txt"
stage NO_ACTION_SERVER_GRAPH_PRECONDITION
timeout 10s ros2 action list > "$OUT/actions_before.txt"
if grep -Eq '^/count_until$' "$OUT/actions_before.txt"; then
  echo 'CH02_26_ACTION_SERVER_PRESENT_PRECONDITION_FAIL' >&2
  exit 2
fi
echo 'CH02_26_NO_SERVER_BEFORE_CLIENT_PASS'

stage ORIGINAL_PYTHON_CLIENT_WAIT_FOR_SERVER_TIMEOUT
export CH02_26_OUT="$OUT"
python3 - <<'PY'
import json,os,subprocess,time
from pathlib import Path
out=Path(os.environ["CH02_26_OUT"])
begin=time.monotonic()
r=subprocess.run(
    ["ros2","run","my_robot_system","count_until_client"],
    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=14.0,
    env=os.environ.copy(),
)
elapsed=time.monotonic()-begin
(out/"client.log").write_text(r.stdout)
print(r.stdout[-2000:],flush=True)
if r.returncode!=0:
    raise RuntimeError(f"CH02_26_CLIENT_EXIT_NOT_ZERO rc={r.returncode}")
if "Action server unavailable" not in r.stdout:
    raise RuntimeError("CH02_26_SERVER_ABSENCE_LOG_MISSING")
if "Waiting for action server (up to 5 s)" not in r.stdout:
    raise RuntimeError("CH02_26_WAIT_LOG_MISSING")
if "Sending goal" in r.stdout or "Goal accepted" in r.stdout:
    raise RuntimeError("CH02_26_UNEXPECTED_GOAL_ATTEMPT")
if not 4.5<=elapsed<=10.0:
    raise RuntimeError(f"CH02_26_WRONG_TIMEOUT elapsed_sec={elapsed}")
result={
  "chapter":"Ch02","section":"2.6",
  "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
  "status":"SCOPED_PASS","scope":"original_Python_action_client_server_missing",
  "no_server_before":True,
  "client_exit_code":r.returncode,
  "measured_wall_seconds":round(elapsed,4),
  "log_contains_server_unavailable":True,
  "no_goal_attempted":True,
  "accepted_goal":"PRESERVED_NOT_RERUN",
  "rejection":"PRESERVED_NOT_RERUN",
  "cancellation":"PRESERVED_NOT_RERUN",
  "server_process":"NOT_STARTED",
  "hardware":"NOT_RUN","ch10":"HOLD",
}
(out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(f"CH02_26_ORIGINAL_ACTION_CLIENT_NO_SERVER_TIMEOUT_PASS duration_sec={elapsed:.3f}",flush=True)
PY
stage SERVER_STILL_ABSENT_AFTER_CLIENT
timeout 10s ros2 action list > "$OUT/actions_after.txt"
if grep -Eq '^/count_until$' "$OUT/actions_after.txt"; then
  echo 'CH02_26_UNEXPECTED_ACTION_SERVER_AFTER_CLIENT_FAIL' >&2
  exit 3
fi
echo 'CH02_26_NO_ACTION_GOAL_NO_SERVER_LEFTOVER_SCOPED_PASS'
