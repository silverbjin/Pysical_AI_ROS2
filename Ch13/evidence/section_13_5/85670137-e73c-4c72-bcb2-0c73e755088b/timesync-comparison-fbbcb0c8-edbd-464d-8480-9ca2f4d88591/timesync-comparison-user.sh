#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
test "$(id -u)" = 1000
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export LP_NUM_THREADS=2
label="task8-g2-sim-cadence-clock-stable-$(basename "$1")"
# The changed phase and its ACK/pause/trajectory/safety neighbours already
# passed 34 tests in task8-reference-phase-drift-green.log. Do not rerun the
# unchanged full subset before each physical discriminator. The orchestrator
# retains the 40s quiet/150s preflight before any ROS receiver/engine, witnesses
# original SYSTEM/MONO and runs its 19 startup/teardown tests. A second identical
# preflight before the non-ROS build adds no engine clock guarantee.
bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/build-native-n.sh "$label"
python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/run-preflight-mujoco-pairs.py --seed-g1-result "$2" --pairs 3
