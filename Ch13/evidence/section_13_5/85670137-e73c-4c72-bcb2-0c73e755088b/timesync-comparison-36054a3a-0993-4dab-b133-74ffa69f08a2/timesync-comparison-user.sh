#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
test "$(id -u)" = 1000
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export LP_NUM_THREADS=2
label="task8-observer-capture-clock-stable-$(basename "$1")"
# The current witness capture/closed-journal/real ROS/cleanup neighbours passed
# 79 tests after their REDs (observer-capture-final-related). The G2 sole-owner
# dispatch and immutable mass math remain unchanged (24/69 prior neighbours).
# Pin the complete encoder source with its final offline cost measurement.
python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/benchmark-observer-encoding.py
# Do not rerun the
# unchanged full subset before each physical discriminator. The orchestrator
# retains the 40s quiet/150s preflight before any ROS receiver/engine, witnesses
# original SYSTEM/MONO and runs its 19 startup/teardown tests. A second identical
# preflight before the non-ROS build adds no engine clock guarantee.
bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/build-native-n.sh "$label"
# Predeclared fixed-source three-pair series: first failed acceptance stops.
python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/run-preflight-mujoco-pairs.py --seed-g1-result "$2" --pairs 3
