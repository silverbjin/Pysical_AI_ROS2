#!/usr/bin/env bash
# Isolated diagnostic only. Docker image must already exist; no pulls or apt installs.
set -u
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
out=${1:?}; seconds=${2:?}; phase=${3:?}
[[ $seconds =~ ^[0-9]+$ && $seconds -ge 1 && $seconds -le 1200 ]] || exit 2
[[ $phase == idle || $phase == docker ]] || exit 2
mkdir -p "$out"
image='ros@sha256:5147d3ae250ce754afd399f6bfec15b33dd4e473ca357e30432a3182031bfad6'
owned=(); pids=(); status=0
tmp=$(mktemp -d)
cleanup(){
  for pid in $(jobs -pr); do kill -TERM "$pid" 2>/dev/null || true; done
  for name in "${owned[@]}"; do docker rm -f "$name" >/dev/null 2>&1 || true; done
  rm -rf -- "$tmp"
}
trap cleanup EXIT
trap 'exit 130' INT TERM
start_container(){
  local label=$1 mode=$2 name
  name="ch15-clock-$(cat /proc/sys/kernel/random/uuid)"
  # Explicit label + unique name; only remove our own containers.
  owned+=("$name")
  mkdir -p "$out/$label-parent"
  timeout -k 10s "$((seconds+120))" docker run --pull never --rm --name "$name" --label ch15.clock.diagnostic=1 \
    --network none --read-only --tmpfs /tmp --user "$(id -u):$(id -g)" \
    -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp -e ROS_LOG_DIR=/tmp/roslog \
    -e ROS_DOMAIN_ID=96 -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
    -v "$root/python:/diag:ro" -v "$(realpath "$out/$label-parent"):/out:rw" \
    --entrypoint bash "$image" -c 'if [[ $1 == ros ]]; then source /opt/ros/jazzy/setup.bash; extra=(--ros); else extra=(); fi; exec python3 /diag/clock_diag.py --scope container_idle --out /out/data --duration "$2" "${extra[@]}"' _ "$mode" "$seconds" \
    > "$out/$label.log" 2>&1 &
  pids+=("$!")
  # Independent RPC brackets against WSL host MONOTONIC; no namespace epoch assumption.
  python3 "$root/python/clock_cross_layer_analyzer.py" "$out" --docker-anchor "$name" --label "$label" --seconds "$seconds" > "$out/$label-anchor.log" 2>&1 &
  pids+=("$!")
}
# Launch host independently; duration is guest MONOTONIC, external QPC measures actual duration.
timeout -k 10s "$((seconds+30))" python3 "$root/python/clock_diag.py" --scope wsl_host --duration "$seconds" --out "$out/host" > "$out/host.log" 2>&1 &
pids+=("$!")
if command -v cc >/dev/null && cc -Wall -Wextra "$root/python/clock_timex_read.c" -o "$tmp/timex" > "$out/timex-build.log" 2>&1; then
  # Sample throughout the window, including final snapshot. No modes other than 0.
  (end=$((SECONDS+seconds)); while (( SECONDS < end )); do "$tmp/timex" || exit 1; sleep 5; done; "$tmp/timex") > "$out/timex-samples.jsonl" 2> "$out/timex-error.log" &
  pids+=("$!")
else
  echo 'NOT_AVAILABLE: no compiler or timex query build failed' > "$out/timex-unavailable.txt"
fi
if [[ $phase == docker ]]; then
  if command -v docker >/dev/null && docker image inspect "$image" >/dev/null 2>&1; then
    start_container container plain
    start_container container_ros ros
  else
    echo 'NOT_AVAILABLE: exact ROS image not locally available' > "$out/docker-unavailable.txt"
    status=1
  fi
  # Bounded single-core synthetic CPU load; no mission and no elevated permissions.
  python3 -c 'import time;end=time.monotonic()+int(__import__("sys").argv[1]);x=1
while time.monotonic()<end: x=(x*1664525+1013904223)&0xffffffff' "$seconds" &
  pids+=("$!")
fi
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
pids=()
for label in container container_ros; do
  [[ ! -d "$out/$label-parent/data" ]] || mv "$out/$label-parent/data" "$out/$label"
done
for name in "${owned[@]}"; do
  if docker container inspect "$name" >/dev/null 2>&1; then echo "OWNED_CONTAINER_REMAINS" >> "$out/status.txt"; status=1; fi
done
printf 'EXIT=%s\nREVIEW_REQUIRED\n' "$status" >> "$out/status.txt"
exit "$status"
