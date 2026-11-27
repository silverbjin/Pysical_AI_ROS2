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
bash /repo/Ch15/scripts/g05_git_lab.sh > /evidence/git-lab.log 2>&1
mkdir /tmp/g05; cd /tmp/g05
colcon build --base-paths /repo/Ch15/ros2_ws/src --event-handlers console_direct+ 2>&1 | tee /evidence/build.log
source install/setup.bash
export G03_INSTALL="$PWD/install" ROS_LOCALHOST_ONLY=1
for pkg in ch15_interfaces ch15_adapters ch15_mission ch15_safety ch15_simulation ch15_visualization; do ros2 pkg prefix "$pkg"; done | tee /evidence/install-prefixes.txt
python3 -m unittest discover -s /repo/Ch15/tests -p 'test_bag_analysis.py' -v
python3 -m unittest discover -s /repo/Ch15/tests -p 'test_replay_isolation.py' -v
colcon test --event-handlers console_direct+
colcon test-result --all --verbose | tee /evidence/colcon-test-result.txt
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
 print(mode,m['events'],m['terminal'])
PY
timeout --signal=INT --kill-after=10s 55s bash /repo/Ch15/scripts/replay_mission.sh /evidence/normal/bag /evidence/replay.json 79 76
echo CH15_G05_T12_T13_T14_PASS
