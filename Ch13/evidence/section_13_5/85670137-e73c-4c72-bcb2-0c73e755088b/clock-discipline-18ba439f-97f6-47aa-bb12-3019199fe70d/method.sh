#!/usr/bin/env bash
set -euo pipefail
repo=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
cd "$repo"
test "$(id -u)" = 1000
base=Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b
root="$base/clock-discipline-$(cat /proc/sys/kernel/random/uuid)"
mkdir "$root"
source_file=.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/read-clock-discipline.c
cp "$source_file" "$root/method.c"
cp .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/read-clock-discipline.sh "$root/method.sh"
cat /proc/sys/kernel/random/boot_id > "$root/boot-id.txt"
uname -a > "$root/kernel.txt"
systemctl show systemd-timesyncd.service --property=ActiveState,SubState,ExecMainPID > "$root/service-before.txt"
cc -std=c11 -O2 -Wall -Wextra -Werror "$root/method.c" -o "$root/reader"
sha256sum "$root/method.c" "$root/method.sh" "$root/reader" > "$root/identity.sha256"
echo "CLOCK_DISCIPLINE $root"
"$root/reader" > "$root/samples.jsonl"
systemctl show systemd-timesyncd.service --property=ActiveState,SubState,ExecMainPID > "$root/service-after.txt"
journalctl -b -u systemd-timesyncd.service --no-pager -n 35 > "$root/service-journal.txt"
sha256sum "$root/samples.jsonl" > "$root/samples.sha256"
echo "CLOCK_DISCIPLINE_CLOSED $root"
