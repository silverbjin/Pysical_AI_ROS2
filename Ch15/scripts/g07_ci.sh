#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive MUJOCO_GL=disable MPLBACKEND=Agg
apt-get update
apt-get install -y --no-install-recommends python3-venv python3-colcon-common-extensions python3-six python3-zipp python3-importlib-resources libgl1 libglfw3 libegl1
source /opt/ros/jazzy/setup.bash
mkdir /tmp/g07; cd /tmp/g07
colcon build --base-paths /repo/Ch15/ros2_ws/src --packages-select ch15_interfaces ch15_adapters ch15_simulation --event-handlers console_direct+ 2>&1 | tee /evidence/build.log
source install/setup.bash
model="$(python3 -c 'from ament_index_python.packages import get_package_share_directory; print(get_package_share_directory("ch15_simulation")+"/models/joint_lab.xml")')"
test -f "${model%/*}/joint_dynamics_example.urdf"
cmp "$model" /repo/Ch15/ros2_ws/src/ch15_simulation/models/joint_lab.xml
sha256sum "$model" "${model%/*}/joint_dynamics_example.urdf" > /evidence/installed-models.sha256
python3 -m venv --system-site-packages /tmp/g07/venv
p=/tmp/g07/venv/bin/python
"$p" -m pip install --only-binary=:all: --no-deps --require-hashes -r /repo/Ch15/requirements/joint.lock.txt 2>&1 | tee /evidence/pip-install.log
"$p" -m pip check | tee /evidence/pip-check.log
"$p" -m pip freeze > /evidence/pip-freeze.txt
dpkg-query -W > /evidence/dpkg-versions.txt
"$p" -m unittest discover -s /repo/Ch15/tests -p test_joint_experiment.py -v 2>&1 | tee /evidence/joint-tests.log
"$p" -m unittest discover -s /repo/Ch15/tests -p test_filter.py -v 2>&1 | tee /evidence/filter-tests.log
"$p" /repo/Ch15/python/pid_experiment.py --model "$model" --out /evidence/joint
"$p" /repo/Ch15/python/robustness_experiment.py --model "$model" --out /evidence/joint
"$p" /repo/Ch15/python/filter_experiment.py --out /evidence/filter
echo CH15_G07_T16_T17_PASS
