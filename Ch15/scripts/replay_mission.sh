#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# == 4 ]] || { echo 'usage: replay_mission.sh BAG NEW_RECEIPT REPLAY_DOMAIN SOURCE_DOMAIN'; exit 2; }
[[ "$3" =~ ^[0-9]+$ && "$4" =~ ^[0-9]+$ && "$3" != "$4" ]] || exit 2
[[ ! -e "$2" ]] || exit 2
export ROS_DOMAIN_ID="$3" ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_STATIC_PEERS ROS_DISCOVERY_SERVER
# G05 local mock only. Keep native publishers/subscribers QoS and safety limits.
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp RMW_FASTRTPS_PUBLICATION_MODE=ASYNCHRONOUS
unset FASTDDS_DEFAULT_PROFILES_FILE FASTRTPS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML
exec python3 "$here/tests/g05_replay_probe.py" "$1" "$2" "$3" "$4"
