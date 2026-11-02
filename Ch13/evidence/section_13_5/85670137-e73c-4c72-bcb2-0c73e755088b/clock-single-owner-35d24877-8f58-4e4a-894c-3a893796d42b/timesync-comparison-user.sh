#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
test "$(id -u)" = 1000
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export LP_NUM_THREADS=2
pair_count="${3:-3}"
engine="${4:-mujoco}"
case "$engine" in mujoco|gazebo) ;; *) exit 2 ;; esac
case "$pair_count" in 1|3) ;; *) exit 2 ;; esac
label="task8-${engine}-applied-elapsed-clock-stable-$(basename "$1")"
# Related RED/GREEN suites run once before source freeze; their exact source
# and logs are in each trial archive. Do not repeat unchanged arithmetic tests
# before each engine discriminator. Retain the eight-package installation audit,
# original-clock admission and actual startup/teardown witness in every session.
bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/build-native-n.sh "$label"
# A one-pair diagnostic uses the just-recorded related source regressions; it is
# explicitly not the required final three-pair consecutive acceptance.
# Predeclared fixed-source three-pair series: first failed acceptance stops.
if [[ "${CH13_CONTACT_COMPONENT:-0}" == 1 ]]; then
  test "$engine" = gazebo && test "$pair_count" = 1
  python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/run-preflight-native-pairs.py --engine "$engine" --pairs 1 --archive-from-native --observer-backend native_cdr --contact-component
else
  python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/run-preflight-native-pairs.py --engine "$engine" --seed-g1-result "$2" --pairs "$pair_count" --archive-from-native --observer-backend native_cdr
fi
