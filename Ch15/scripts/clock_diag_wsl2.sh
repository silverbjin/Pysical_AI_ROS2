#!/usr/bin/env bash
# Read-only configuration queries; no sudo, service restart or clock write.
set -u
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ ${1:-} == anchor ]]; then
  PYTHONPATH="$root/python" python3 -c 'import json;from clock_diag import sample;print(json.dumps(sample(scope="wsl_host")))'
  exit $?
fi
out=${1:?output directory}; seconds=${2:?seconds}; phase=${3:?phase}
[[ $seconds =~ ^[0-9]+$ && $seconds -ge 1 && $seconds -le 1200 ]] || exit 2
[[ $phase == idle || $phase == docker ]] || exit 2
mkdir -p "$out"
query(){ local name=$1; shift; { printf 'COMMAND: %s\n' "$1"; timeout 15s "$@"; rc=$?; printf '\nEXIT=%s\n' "$rc"; [[ $rc == 0 ]] || echo NOT_AVAILABLE; } > "$out/$name.txt" 2>&1; }
query kernel uname -srmo
query clocksource cat /sys/devices/system/clocksource/clocksource0/current_clocksource /sys/devices/system/clocksource/clocksource0/available_clocksource
query boot cat /proc/cmdline
query cpu lscpu
query timedatectl timedatectl status
query timesync timedatectl show-timesync --all
query services systemctl show systemd-timesyncd chrony chronyd ntp ntpsec -p ActiveState -p UnitFileState -p MainPID
query ntpconfig sh -c 'for f in /etc/systemd/timesyncd.conf /etc/chrony/chrony.conf /etc/ntp.conf; do if [ -r "$f" ]; then printf "\n%s\n" "$f"; cat "$f"; fi; done'
query timex adjtimex --print
query ntptime ntptime
query chrony chronyc tracking
query journal journalctl -b -u systemd-timesyncd -u chrony -u ntp -n 200 --no-pager
query dmesg dmesg
query docker_version docker version
exec bash "$root/scripts/clock_diag_cross_layer.sh" "$out" "$seconds" "$phase"
