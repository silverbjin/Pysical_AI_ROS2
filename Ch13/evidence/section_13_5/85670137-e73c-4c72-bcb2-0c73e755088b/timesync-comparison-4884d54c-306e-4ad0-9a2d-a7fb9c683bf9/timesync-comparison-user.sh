#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
test "$(id -u)" = 1000
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export LP_NUM_THREADS=2
label="task8-g2-sim-cadence-clock-stable-$(basename "$1")"
# Immutable mass compilation passed 69 parity/support/gait/safety neighbours
# (static-mass-parity-related), after its RED and initial23. The interleaved
# actual-state math comparison preserves values and reduces CPU ~49%.
# Thread CPU attribution already passed8 (decision-thread-cpu-green). Do not rerun the
# unchanged full subset before each physical discriminator. The orchestrator
# retains the 40s quiet/150s preflight before any ROS receiver/engine, witnesses
# original SYSTEM/MONO and runs its 19 startup/teardown tests. A second identical
# preflight before the non-ROS build adds no engine clock guarantee.
bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/build-native-n.sh "$label"
# Predeclared fixed-source three-pair series: first failed acceptance stops.
python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/run-preflight-mujoco-pairs.py --seed-g1-result "$2" --pairs 3
