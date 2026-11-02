#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
test "$(id -u)" = 1000
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export LP_NUM_THREADS=2
python Ch13/scripts/check_system_clock_13_5.py --output-dir "$1/preflight"
label="task8-g2-sim-cadence-clock-stable-$(basename "$1")"
tests=Ch13/ros2_ws/src/integrated_robot_navigation/test
CH13_TEST_DOMAIN_ID=221 bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/check-native.sh "$label" \
    "$tests/test_g2_control_cadence_ros.py" "$tests/test_control_clock_dispatch.py" \
    "$tests/test_crawl_safety_ros.py" "$tests/test_gait_reference_credit.py" \
    "$tests/test_g2_scoped_nodes.py" "$tests/test_fault_hold_stop_ros.py" \
    "$tests/test_fault_hold_stop.py" "$tests/test_reference_dispatch.py" \
    "$tests/test_reference_dispatch_ros.py" "$tests/test_reference_dispatch_phase_ros.py" \
    "$tests/test_applied_reference_ros.py" \
    "$tests/test_crawl_ingress_dispatch.py" -W error
bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/build-native-n.sh "$label"
python .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/run-preflight-mujoco-pairs.py --seed-g1-result "$2" --pairs 3
