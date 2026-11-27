#!/usr/bin/env bash
# Runs only inside the digest-pinned isolated CPU/Gazebo container.
set -eo pipefail
kind="$1"
CH=/repo/Ch15
export DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
unset ROS_STATIC_PEERS ROS_DISCOVERY_SERVER CYCLONEDDS_URI RMW_FASTRTPS_PUBLICATION_MODE FASTDDS_DEFAULT_PROFILES_FILE FASTRTPS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML
if [[ "$kind" == joint ]]; then
  bash "$CH/scripts/g07_ci.sh"
  printf '{"result":"PASS","scope":"no ROS graph launched (joint)"}\n' > /evidence/residual.json
  exit 0
fi
# G04 T11 qualified on the image default RMW, without mock-specific DDS overrides.
if [[ "$kind" == cube ]]; then
  unset RMW_IMPLEMENTATION ROS_LOCALHOST_ONLY ROS_AUTOMATIC_DISCOVERY_RANGE
fi
apt-get update
common=(python3-colcon-common-extensions ros-jazzy-nav2-msgs ros-jazzy-tf2-ros ros-jazzy-tf2-ros-py ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-rosbag2 ros-jazzy-rosbag2-storage-mcap python3-yaml)
case "$kind" in
  cube) extra=(python3-opencv python3-numpy ros-jazzy-cv-bridge ros-jazzy-ros-gz-bridge); pkgs=(ch15_interfaces ch15_adapters ch15_simulation);;
  markers) extra=(ros-jazzy-visualization-msgs ros-jazzy-ros2launch ros-jazzy-rviz2);pkgs=(ch15_interfaces ch15_visualization);;
  build) extra=(python3-rosdep python3-opencv python3-numpy ros-jazzy-cv-bridge ros-jazzy-py-trees ros-jazzy-visualization-msgs ros-jazzy-ros2launch ros-jazzy-rviz2);pkgs=();;
  mock|faults|icd|analysis) extra=(ros-jazzy-py-trees python3-matplotlib ros-jazzy-nav2-behaviors);pkgs=(ch15_interfaces ch15_adapters ch15_safety ch15_mission);;
  *) exit 2;;
esac
apt-get install -y --no-install-recommends "${common[@]}" "${extra[@]}"
source /opt/ros/jazzy/setup.bash
if [[ "$kind" == build ]]; then
  if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then rosdep init; fi
  rosdep update --rosdistro jazzy
  rosdep install --from-paths "$CH/ros2_ws/src" --ignore-src --rosdistro jazzy -y
  rosdep check --from-paths "$CH/ros2_ws/src" --ignore-src --rosdistro jazzy | tee /evidence/rosdep-check.log
fi
dpkg-query -W > /evidence/dpkg-versions.txt
mkdir /tmp/ch15-owner-ws;cd /tmp/ch15-owner-ws
opts=(); if (( ${#pkgs[@]} )); then opts=(--packages-select "${pkgs[@]}");fi
colcon build --base-paths "$CH/ros2_ws/src" "${opts[@]}" --event-handlers console_direct+ 2>&1 | tee /evidence/build.log
source install/setup.bash
export G03_INSTALL="$PWD/install" G02_INSTALL="$PWD/install"
domains=()
case "$kind" in
 build)
  for pkg in ch15_interfaces ch15_adapters ch15_safety ch15_mission ch15_simulation ch15_visualization; do ros2 pkg prefix "$pkg"; done | tee /evidence/install-prefixes.txt
  colcon test --event-handlers console_direct+
  colcon test-result --all --verbose | tee /evidence/colcon-test-result.txt
  python3 "$CH/python/g05_lock.py" "$CH" > /evidence/lock.json
  for t in test_scenarios.py test_world_contract.py test_icd.py test_g02_contract.py test_action_supervisor.py test_target_contract.py test_mission_tree.py test_bag_analysis.py test_replay_isolation.py test_markers.py test_g08_contracts.py; do
    python3 -m unittest discover -s "$CH/tests" -p "$t" -v 2>&1 | tee "/evidence/$t.log"
  done
  timeout 15s ros2 launch ch15_mission mission.launch.py --show-args > /evidence/launch-args.txt
  timeout 15s ros2 launch ch15_visualization visualization.launch.xml --show-args > /evidence/visualization-args.txt
  export ROS_DOMAIN_ID=70; domains=(70);;
 icd)
  export ROS_DOMAIN_ID=71;domains=(71)
  for iface in action/PickObject action/PlaceObject srv/SwitchGait msg/MissionStatus msg/TargetObservation msg/SafetyState msg/ReadyState msg/MissionEvent; do ros2 interface show "ch15_interfaces/$iface" > "/evidence/${iface//\//_}.txt";done
  timeout --signal=INT --kill-after=20s 100s python3 "$CH/tests/g02_dds_probe.py" /evidence/dds;;
 mock)
  domains=(76 79)
  timeout --signal=INT --kill-after=20s 100s bash "$CH/scripts/record_mission.sh" normal /evidence/normal 76
  python3 "$CH/python/bag_to_csv.py" /evidence/normal/bag /evidence/normal/analysis
  python3 "$CH/python/plot_mission.py" /evidence/normal/analysis
  timeout --signal=INT --kill-after=10s 55s bash "$CH/scripts/replay_mission.sh" /evidence/normal/bag /evidence/replay.json 79 76;;
 analysis)
  domains=(79)
  python3 "$CH/python/bag_to_csv.py" /input-bag /evidence/analysis
  python3 "$CH/python/plot_mission.py" /evidence/analysis
  timeout --signal=INT --kill-after=10s 55s bash "$CH/scripts/replay_mission.sh" /input-bag /evidence/replay.json 79 76;;
 cube)
  export ROS_DOMAIN_ID=95 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST;domains=(95 79)
  for mode in SIGINT SIGTERM exception; do
    timeout --signal=INT --kill-after=5s 20s python3 "$CH/tests/g09_detector_shutdown_probe.py" "$mode" "/evidence/detector-shutdown-probe-$mode.json"
  done
  export ROS_DOMAIN_ID=79
  bash "$CH/scripts/run_cube_lab.sh" /evidence/cube;;
 markers)
  export ROS_DOMAIN_ID=85;domains=(85)
  timeout --signal=INT --kill-after=10s 90s python3 "$CH/tests/g06_marker_probe.py" /evidence/marker-capture.json
  timeout --signal=INT --kill-after=10s 45s python3 "$CH/tests/g06_clock_probe.py" /evidence/clock-capture.json;;
 faults)
  cases=(F03_transient:90 F03_persistent:91 F04:92 F06:93 F01:94)
  for row in "${cases[@]}"; do
    mode="${row%:*}";domain="${row#*:}"
    [[ -z "$CH15_FAULT_SCENARIO" || "$mode" == "$CH15_FAULT_SCENARIO" ]] || continue
    export ROS_DOMAIN_ID="$domain";domains+=("$domain")
    timeout --signal=INT --kill-after=20s 100s python3 "$CH/tests/g08_record_probe.py" "$mode" "/evidence/$mode"
    python3 "$CH/python/g08_analyze.py" "/evidence/$mode" "$mode"
  done
  python3 "$CH/tests/g08_nav2_plugin_audit.py" /evidence/nav2-plugin-audit.json;;
esac
python3 "$CH/scripts/owner_graph_audit.py" /evidence/residual.json "${domains[@]}"
echo CH15_OWNER_RUNTIME_PASS "$kind"
