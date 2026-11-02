#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
test "$(id -u)" = 1000
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export LP_NUM_THREADS=2
python Ch13/scripts/check_system_clock_13_5.py --output-dir "$1/preflight"
label="task8-g2-sim-cadence-clock-stable-$(basename "$1")"
# The changed timer boundary and its ACK/pause/trajectory neighbours already
# passed 22 tests in task8-early-reference-timer-green.log. Do not rerun the
# unchanged full subset before each physical discriminator. The orchestrator
# still witnesses original SYSTEM/MONO and runs its 19 startup/teardown tests.
bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/build-native-n.sh "$label"
python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/run-preflight-mujoco-pairs.py --seed-g1-result "$2" --pairs 3
