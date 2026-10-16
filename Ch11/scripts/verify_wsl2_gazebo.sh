#!/usr/bin/env bash
# Run from the repository checkout on the user's WSL2 host.
# Starts only this experiment; never kills unrelated Gazebo/ROS processes.
set -eo pipefail
ch11_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
evidence_dir="${CH11_EVIDENCE_DIR:-$ch11_root/evidence/wsl2-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$evidence_dir"
exec > >(tee "$evidence_dir/runner.log") 2>&1
printf 'Evidence: %s\n' "$evidence_dir"
uname -a
git -C "$ch11_root" rev-parse HEAD > "$evidence_dir/source_commit.txt"
git -C "$ch11_root" diff --stat > "$evidence_dir/source_diff.txt"
runtime_started=false
launch_pid=""
cleanup() {
  script_rc=$?
  if [ -n "$launch_pid" ]; then
    kill -INT -- "-$launch_pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 "$launch_pid" 2>/dev/null || break
      sleep 0.5
    done
    kill -TERM -- "-$launch_pid" 2>/dev/null || true
    wait "$launch_pid" 2>/dev/null || true
  fi
  if [ ! -f "$evidence_dir/result.json" ]; then
    python3 - "$evidence_dir/result.json" "$script_rc" "$runtime_started" <<'PY'
import json,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
    "status":"FAIL", "runner_exit":int(sys.argv[2]),
    "runtime_executed":sys.argv[3]=="true",
    "reason":"Runner exited before completion; inspect runner.log."}, indent=2)+"\n")
PY
  fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM
block() {
  printf 'BLOCKED: %s\n' "$1"
  python3 - "$evidence_dir/result.json" "$1" <<'PY'
import json,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps(
    {"status":"BLOCKED","reason":sys.argv[2],"runtime_executed":False}, indent=2)+"\n")
PY
  exit 2
}
grep -qi 'microsoft.*wsl2' /proc/sys/kernel/osrelease ||
  block "This host is not WSL2; cannot certify the requested environment."
test -f /opt/ros/jazzy/setup.bash || block "ROS 2 Jazzy not installed."
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
for executable in ros2 gz colcon setsid timeout; do
  command -v "$executable" >/dev/null || block "Missing command: $executable"
done
python3 -c 'import rclpy, numpy, yaml, pytest' || block "Missing system Python dependencies."
if [ -n "${VIRTUAL_ENV:-}" ] || [ -n "${CONDA_PREFIX:-}" ]; then
  block "Deactivate Python virtual environments before running."
fi
# Isolated DDS domain. Never silently share the user's active experiment.
export ROS_DOMAIN_ID="${CH11_DOMAIN_ID:-71}"
ros2 daemon stop || true
existing="$(timeout 10s ros2 node list --no-daemon)" ||
  block "Cannot inspect ROS graph."
test -z "$existing" || block "ROS_DOMAIN_ID already contains nodes; choose CH11_DOMAIN_ID."
printf 'ROS_DOMAIN_ID=%s\n' "$ROS_DOMAIN_ID"
gz sim --versions
cd "$ch11_root/ros2_ws"
colcon build --symlink-install --packages-up-to my_quadruped_bot 2>&1 |
  tee "$evidence_dir/build.log"
source install/setup.bash
prefix="$(ros2 pkg prefix my_quadruped_bot)"
case "$prefix" in
  "$ch11_root/ros2_ws/install"/*) ;;
  *) block "Wrong chapter overlay: $prefix" ;;
esac
python3 -m unittest discover -s "$ch11_root/tests" -v 2>&1 |
  tee "$evidence_dir/unit.log"
set +e
colcon test --packages-select my_quadruped_bot --event-handlers console_direct+ > "$evidence_dir/colcon-test.log" 2>&1
test_rc=$?
colcon test-result --verbose > "$evidence_dir/colcon-test-result.log" 2>&1
result_rc=$?
set -e

# Isolate Gazebo Transport as well as DDS.
export GZ_PARTITION="ch11_verify_$$"
setsid ros2 launch my_quadruped_bot ch11_bringup.launch.py > "$evidence_dir/bringup.log" 2>&1 &
launch_pid=$!
runtime_started=true
set +e
timeout --signal=INT --kill-after=10s 140s python3 "$ch11_root/scripts/verify_runtime.py" \
  --motion --output "$evidence_dir/runtime.json" > "$evidence_dir/probe.log" 2>&1
probe_rc=$?
set -e
python3 - "$evidence_dir" "$test_rc" "$result_rc" "$probe_rc" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
codes=dict(zip(("colcon_test","colcon_test_result","runtime_probe"), map(int,sys.argv[2:])))
runtime=json.loads((p/"runtime.json").read_text()) if (p/"runtime.json").exists() else {"status":"MISSING"}
passed=not any(codes.values()) and runtime["status"]=="PASS"
result={"status":"PASS" if passed else "FAIL","runtime_executed":True,
        "exit_codes":codes,"runtime":runtime,
        "scope":"WSL2/Jazzy/Gazebo sensor + localization + short motion; not complete navigation"}
(p/"result.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
sys.exit(0 if passed else 1)
PY
