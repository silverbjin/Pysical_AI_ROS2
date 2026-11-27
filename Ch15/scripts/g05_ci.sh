#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends git git-lfs python3-rosdep python3-colcon-common-extensions python3-pytest python3-yaml python3-matplotlib ros-jazzy-rosbag2 ros-jazzy-rosbag2-storage-mcap ros-jazzy-py-trees
source /opt/ros/jazzy/setup.bash
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then rosdep init; fi
rosdep update --rosdistro jazzy
if rosdep resolve ch15_deliberately_missing_g05_key --rosdistro jazzy; then exit 1; fi
rosdep install --from-paths /repo/Ch15/ros2_ws/src --ignore-src --rosdistro jazzy -y
rosdep check --from-paths /repo/Ch15/ros2_ws/src --ignore-src --rosdistro jazzy | tee /evidence/rosdep-check.log
dpkg-query -W > /evidence/dpkg-versions.txt
python3 /repo/Ch15/python/g05_lock.py /repo/Ch15 | tee /evidence/lock.json
python3 -m unittest discover -s /repo/Ch15/tests -p 'test_g05_lock.py' -v
# RED1 git/lfs actual PASS reused; no repeat in record-focused retry.
printf 'REUSE run45946312887 artifact15174419809 git-lab.log\n' > /evidence/git-lab-reuse.txt
mkdir /tmp/g05; cd /tmp/g05
colcon build --base-paths /repo/Ch15/ros2_ws/src --event-handlers console_direct+ 2>&1 | tee /evidence/build.log
source install/setup.bash
export G03_INSTALL="$PWD/install" ROS_LOCALHOST_ONLY=1
for pkg in ch15_interfaces ch15_adapters ch15_mission ch15_safety ch15_simulation ch15_visualization; do ros2 pkg prefix "$pkg"; done | tee /evidence/install-prefixes.txt
python3 -m unittest discover -s /repo/Ch15/tests -p 'test_bag_analysis.py' -v
python3 -m unittest discover -s /repo/Ch15/tests -p 'test_replay_isolation.py' -v
colcon test --event-handlers console_direct+
colcon test-result --all --verbose | tee /evidence/colcon-test-result.txt
# No package-local tests are installed yet; explicit cross-package tests above are authoritative.
python3 - <<'PY'
import ch15_interfaces.msg, ch15_adapters.mock_servers, ch15_safety.readiness_monitor, ch15_mission.mission_executor, ch15_simulation.cube_detector, ch15_visualization
print('G05_INSTALLED_IMPORTS_6_OF_6')
PY
printf 'REUSE run45947575404 artifact15175486140 demo-smoke/demo_result.json\n' > /evidence/demo-reuse.txt
# G05 local mock only. Keep native publishers/subscribers QoS and safety limits.
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp RMW_FASTRTPS_PUBLICATION_MODE=ASYNCHRONOUS
unset FASTDDS_DEFAULT_PROFILES_FILE FASTRTPS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML
python3 - <<'PY' | tee /evidence/rmw.json
import json,os
from rclpy.utilities import get_rmw_implementation_identifier
actual=get_rmw_implementation_identifier()
assert actual=='rmw_fastrtps_cpp'
print(json.dumps(dict(rmw=actual,publication_mode=os.environ['RMW_FASTRTPS_PUBLICATION_MODE'])))
PY
# No motion. Qualify actual timing before any normal mission.
timeout --signal=INT --kill-after=15s 60s python3 /repo/Ch15/tests/g05_scan_diag.py /evidence/async-qualification --async-qualify
for row in normal:76 F01:77 F06:78; do
  mode="${row%:*}"; domain="${row#*:}"
  timeout --signal=INT --kill-after=20s 90s bash /repo/Ch15/scripts/record_mission.sh "$mode" "/evidence/$mode" "$domain"
  python3 /repo/Ch15/python/bag_to_csv.py "/evidence/$mode/bag" "/evidence/$mode/analysis"
  python3 /repo/Ch15/python/plot_mission.py "/evidence/$mode/analysis"
done
python3 - <<'PY'
import csv,json,pathlib
for mode in ('normal','F01','F06'):
 p=pathlib.Path('/evidence')/mode
 rows=list(csv.DictReader((p/'analysis/events.csv').open()))
 orig=[json.loads(x) for x in (p/'executor/mission-events.jsonl').read_text().splitlines()]
 assert len(rows)==len(orig)
 for a,b in zip(rows,orig):
  assert all(str(b[k])==a[k] for k in ('mission_id','epoch','producer','event_seq','steady_ns','ros_ns','event','request_id','goal_uuid','source')) and json.loads(a['detail'])==b['detail']
 m=json.loads((p/'analysis/metrics.json').read_text());assert m['terminal']==('COMPLETED' if mode=='normal' else 'ABORTED')
 assert m['energy_j'] is None
 if mode=='normal':assert m['goals']==4 and m['rejected_goals']==0
 if mode=='F01':assert any(x['event']=='FAULT' for x in orig) and any(x['event']=='STOP_OBSERVED' for x in orig) and any(x['event']=='GOAL_ACCEPTED' for x in orig)
 if mode=='F06':assert any(x['event']=='STEP_ENTER' and x['detail']['step']=='pick_retract' for x in orig) and any(x['event']=='GOAL_TERMINAL' and x['detail']['status']==6 for x in orig)
 print(mode,m['events'],m['terminal'])
PY
timeout --signal=INT --kill-after=10s 55s bash /repo/Ch15/scripts/replay_mission.sh /evidence/normal/bag /evidence/replay.json 79 76
echo CH15_G05_T12_T13_T14_PASS
