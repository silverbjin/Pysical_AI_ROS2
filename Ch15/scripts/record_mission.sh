#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# == 3 ]] || { echo 'usage: record_mission.sh normal|F01|F06 NEW_OUT MOCK_DOMAIN'; exit 2; }
: "${G03_INSTALL:?source the clean Ch15 workspace and set G03_INSTALL to its absolute install path}"
[[ "$3" =~ ^[0-9]+$ ]] && (( 1 <= $3 && $3 <= 232 )) || exit 2
export ROS_DOMAIN_ID="$3" ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS ROS_DISCOVERY_SERVER
# G05 local mock only. Keep native publishers/subscribers QoS and safety limits.
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
unset RMW_FASTRTPS_PUBLICATION_MODE CYCLONEDDS_URI
unset FASTDDS_DEFAULT_PROFILES_FILE FASTRTPS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML
exec python3 "$here/tests/g05_record_probe.py" "$1" "$2"
