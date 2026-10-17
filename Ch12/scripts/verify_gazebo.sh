#!/usr/bin/env bash
# Run the existing Ch11 robot; isolate this experiment's DDS and transport.
set -eo pipefail
chapter="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo="$(dirname "$chapter")"
evidence="${CH12_GAZEBO_EVIDENCE:-$chapter/evidence/gazebo}"
mkdir -p "$evidence"
evidence="$(cd "$evidence" && pwd)"
exec > >(tee "$evidence/runner.log") 2>&1
launch_pid=""
group_alive() {
  # An exited but unreaped launch parent is a zombie, not a running process.
  ps -eo pgid=,stat= | awk -v target="$launch_pid" \
    '$1 == target && $2 !~ /^Z/ {alive=1} END {exit !alive}'
}
python3 - "$evidence" <<'PY'
from pathlib import Path
import sys
for name in ('result.json', 'observation.json', 'launch.log', 'server_stop.log'):
    Path(sys.argv[1], name).unlink(missing_ok=True)
PY
cleanup() {
  rc=$?
  trap - EXIT
  set +e
  forced=false
  if [ -n "$launch_pid" ]; then
    # Stop this partition's server via its API; the GUI/CLI wrapper then exits
    # normally instead of requiring launch to escalate a shell-child signal.
    timeout --kill-after=2s 12s gz service -s /server_control --reqtype gz.msgs.ServerControl \
      --reptype gz.msgs.Boolean --timeout 8000 --req 'stop: true' \
      > "$evidence/server_stop.log" 2>&1
    # A positive response precedes CLI exit. Let launch reap it before SIGINT,
    # otherwise an already-stopping Gazebo may be reported as signal -2.
    for _ in $(seq 1 40); do
      grep -Fq '[gazebo-1]: process has finished cleanly' "$evidence/launch.log" && break
      group_alive || break
      sleep 0.25
    done
    # launch forwards SIGINT itself; signalling its whole group can deliver twice.
    kill -INT "$launch_pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      group_alive || break
      sleep 0.5
    done
    if group_alive; then
      forced=true
      kill -TERM -- "-$launch_pid" 2>/dev/null || true
      for _ in $(seq 1 10); do
        group_alive || break
        sleep 0.5
      done
      kill -KILL -- "-$launch_pid" 2>/dev/null || true
    fi
    wait "$launch_pid" 2>/dev/null || true
  fi
  python3 - "$evidence" "$rc" "$forced" <<'PY'
import json
from pathlib import Path
import sys
p = Path(sys.argv[1])
rc = int(sys.argv[2])
observation = json.loads((p/'observation.json').read_text()) if (p/'observation.json').exists() else {}
log = (p/'launch.log').read_text(errors='replace') if (p/'launch.log').exists() else ''
stop_log = (p/'server_stop.log').read_text(errors='replace') if (p/'server_stop.log').exists() else ''
stop_ack = 'data: true' in stop_log
clean = bool(log) and 'Traceback' not in log and '[ERROR]' not in log and sys.argv[3] == 'false' and stop_ack
passed = rc == 0 and observation.get('status') == 'PASS' and clean
result = dict(status='PASS' if passed else 'FAIL', observation=observation,
              shutdown_clean=clean, gazebo_stop_ack=stop_ack,
              forced_cleanup=sys.argv[3] == 'true', runner_exit=rc)
(p/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
sys.exit(0 if passed else 1)
PY
  summary_rc=$?
  if [ "$rc" -eq 0 ]; then rc=$summary_rc; fi
  printf 'Runner exit: %s\n' "$rc"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT TERM
test -z "${VIRTUAL_ENV:-}${CONDA_PREFIX:-}" || { echo 'Deactivate venv/Conda first.'; exit 2; }
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID="${CH12_DOMAIN_ID:-82}"
export GZ_PARTITION="ch12_1_$$"
# Do not reuse an active ROS experiment.
nodes="$(timeout 15s ros2 node list --no-daemon)"
test -z "$nodes" || { echo 'Choose an unused CH12_DOMAIN_ID.'; exit 2; }
uname -a
gz sim --versions
git -C "$repo" rev-parse HEAD > "$evidence/source_commit.txt"
git -c core.autocrlf=true -C "$repo" diff --stat > "$evidence/source_diff.txt"
git -c core.autocrlf=true -C "$repo" status --short > "$evidence/source_status.txt"
python3 -m unittest discover -s "$repo/Ch11/tests" -v > "$evidence/ch11_tests.log" 2>&1
cd "$repo/Ch11/ros2_ws"
colcon build --symlink-install --packages-up-to my_quadruped_bot 2>&1 | tee "$evidence/build.log"
source install/setup.bash
prefix="$(ros2 pkg prefix my_quadruped_bot)"
case "$prefix" in
  "$repo/Ch11/ros2_ws/install/"*) ;;
  *) echo "Wrong overlay: $prefix"; exit 2 ;;
esac
# Bash background jobs may inherit ignored SIGINT. Reset it before exec so
# launch can install its handler and forward one orderly shutdown to children.
setsid python3 -c 'import os, signal, sys; signal.signal(signal.SIGINT, signal.SIG_DFL); os.execvp(sys.argv[1], sys.argv[1:])' \
  ros2 launch my_quadruped_bot SLAM_simulation.launch.py start_rviz:=false \
  > "$evidence/launch.log" 2>&1 &
launch_pid=$!
# Existing read-only probe checks actual pose, six streams, LiDAR and TF.
timeout --signal=INT --kill-after=10s 190s python3 \
  "$repo/Ch11/evidence/figure_11_2_redebug_20261017/repeat_probe.py" \
  --duration 30 --output "$evidence/observation.json" > "$evidence/probe.log" 2>&1
