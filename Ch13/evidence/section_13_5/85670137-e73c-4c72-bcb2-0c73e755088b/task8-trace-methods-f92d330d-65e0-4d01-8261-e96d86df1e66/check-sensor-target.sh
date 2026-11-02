#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
label=${1:?unique label};target=${2:?test target}
export ROS_DOMAIN_ID=159
test ! -e "$CH13_NAV_EVIDENCE/$label.log"
set +e
{
  cmake -S Ch13/ros2_ws/src/integrated_robot_navigation_sensors -B "$CH13_NAV_BUILD/integrated_robot_navigation_sensors" -DBUILD_TESTING=ON &&
    cmake --build "$CH13_NAV_BUILD/integrated_robot_navigation_sensors" --target "$target" -j2 &&
    "$CH13_NAV_BUILD/integrated_robot_navigation_sensors/$target"
} > "$CH13_NAV_EVIDENCE/$label.log" 2>&1
result=$?
tail -n35 "$CH13_NAV_EVIDENCE/$label.log"
exit "$result"
