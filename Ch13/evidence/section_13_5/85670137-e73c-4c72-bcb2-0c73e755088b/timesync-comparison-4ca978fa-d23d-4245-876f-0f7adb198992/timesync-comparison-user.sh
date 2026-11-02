#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
test "$(id -u)" = 1000
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export LP_NUM_THREADS=2
label="task8-applied-elapsed-clock-stable-$(basename "$1")"
# The current scoped high-level curve law passed43 clock/ACK/speed/STOP/scope
# neighbours (applied-elapsed-final-corrected). The unchanged witness passed79;
# its source-pinned ad0099 benchmark remains valid. Do not rerun the
# unchanged full subset before each physical discriminator. The orchestrator
# retains the 40s quiet/150s preflight before any ROS receiver/engine, witnesses
# original SYSTEM/MONO and runs its 19 startup/teardown tests. A second identical
# preflight before the non-ROS build adds no engine clock guarantee.
bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/build-native-n.sh "$label"
# Predeclared fixed-source three-pair series: first failed acceptance stops.
python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/run-preflight-mujoco-pairs.py --seed-g1-result "$2" --pairs 3
