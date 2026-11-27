#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3-colcon-common-extensions python3-yaml ros-jazzy-visualization-msgs ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-ros2launch ros-jazzy-rviz2
source /opt/ros/jazzy/setup.bash
mkdir /tmp/g06; cd /tmp/g06
colcon build --base-paths /repo/Ch15/ros2_ws/src --packages-select ch15_interfaces ch15_visualization --event-handlers console_direct+ 2>&1 | tee /evidence/build.log
source install/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=85 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
python3 -m unittest discover -s /repo/Ch15/tests -p test_markers.py -v 2>&1 | tee /evidence/unit.log
python3 - <<'PY' | tee /evidence/config-audit.json
import json,yaml,xml.etree.ElementTree as ET
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
p=Path(get_package_share_directory('ch15_visualization'))
r={}
for name in ('debug','presentation'):
 d=yaml.safe_load((p/'rviz'/f'{name}.rviz').read_text())['Visualization Manager']
 assert d['Global Options']['Fixed Frame']=='map'
 assert {t['Class'] for t in d['Tools']}=={'rviz_default_plugins/MoveCamera','rviz_default_plugins/Select'}
 assert {x['Marker Topic']['Value'] for x in d['Displays'] if x['Class']=='rviz_default_plugins/Marker'}=={'/ch15/visualization/target','/ch15/visualization/status'}
 r[name]='PASS'
ET.parse(p/'launch/visualization.launch.xml')
print(json.dumps(r))
PY
ros2 launch ch15_visualization visualization.launch.xml --show-args | tee /evidence/launch-args.log
timeout --signal=INT --kill-after=10s 90s python3 /repo/Ch15/tests/g06_marker_probe.py /evidence/marker-capture.json
echo CH15_G06_T15_PASS
