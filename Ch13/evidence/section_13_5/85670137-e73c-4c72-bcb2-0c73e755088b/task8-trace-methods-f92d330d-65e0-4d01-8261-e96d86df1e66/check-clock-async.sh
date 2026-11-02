#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export ROS_DOMAIN_ID=159
label=${1:?unique label}
shift
if (( $#==0 )); then set -- test_async_trace test_control_clock_gate test_control_clock_ros;fi
test ! -e "$CH13_NAV_EVIDENCE/$label.log"
set +e
(
  set -e
  for target in "$@";do "$CH13_NAV_BUILD/integrated_robot_navigation_sensors/$target";done
) > "$CH13_NAV_EVIDENCE/$label.log" 2>&1
result=$?
tail -n45 "$CH13_NAV_EVIDENCE/$label.log"
exit "$result"
