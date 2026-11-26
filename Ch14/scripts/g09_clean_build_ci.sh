#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=locked_environment
trap 'rc=$?; printf "{\"stage\":\"%s\",\"exit_code\":%s}\n" "$stage" "$rc" > "$out/stage.json"' EXIT
# Apply the already observed G08 mirror correction inside this container only.
for f in /etc/apt/sources.list /etc/apt/sources.list.d/ubuntu.sources; do
 if [[ -f "$f" ]]; then sed -i -e 's|http://archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' -e 's|http://security.ubuntu.com/ubuntu|https://security.ubuntu.com/ubuntu|g' "$f"; fi
done
printf '%s\n' 'Acquire::Retries "2";' 'Acquire::http::No-Cache "true";' 'Acquire::https::No-Cache "true";' 'APT::Update::Error-Mode "any";' > /etc/apt/apt.conf.d/99g09
test -s /ch14/requirements/rl.lock.txt
source /ch14/scripts/g07_env.sh "$out"
apt-get install -y --no-install-recommends ros-jazzy-cv-bridge ros-jazzy-vision-msgs ros-jazzy-message-filters ros-jazzy-tf2-ros-py ros-jazzy-diagnostic-msgs ros-jazzy-rosgraph-msgs ros-jazzy-ros-gz-bridge ros-jazzy-ros-gz-sim ros-jazzy-tf2-ros ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-ament-cmake ros-jazzy-std-srvs ros-jazzy-visualization-msgs ros-jazzy-xacro >/dev/null
dpkg-query -W > "$out/dpkg-versions.txt"
stage=clean_build
mkdir -p /tmp/g09_ws/src
cp -a /ch14/ros2_ws/src/. /tmp/g09_ws/src/
(cd /tmp/g09_ws && python "$(command -v colcon)" build --packages-select ch14_ai_common ch14_ai_interfaces ch14_ai_perception ch14_performance_monitor ch14_rl_deployment ch14_simulation --cmake-args -DPython3_EXECUTABLE="$(command -v python)") 2>&1 | tee "$out/colcon.log"
set +u
source /tmp/g09_ws/install/setup.bash
set -u
stage=installed_contract
cd /tmp
export ROS_DOMAIN_ID=102 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
python -m pip check | tee "$out/pip-check.txt"
for p in ch14_ai_common ch14_ai_interfaces ch14_ai_perception ch14_performance_monitor ch14_rl_deployment ch14_simulation; do
 ros2 pkg prefix "$p"
 ros2 pkg executables "$p"
done > "$out/packages.txt"
ros2 interface show ch14_ai_interfaces/srv/SwapModel > "$out/service.txt"
ros2 launch ch14_ai_perception robot_ai_system.launch.py --show-args > "$out/launch-ai.txt"
ros2 launch ch14_simulation semantic_rgbd.launch.py --show-args > "$out/launch-scene.txt"
python - <<'PY' > "$out/imports.txt"
import numpy,torch,onnxruntime,rclpy
from cv_bridge import CvBridge
from ch14_ai_common.backends import OrtBackend
from ch14_rl_deployment.policy import OnnxPolicy
from ch14_rl_deployment.rl_controller import RLController
from ch14_rl_deployment.mujoco_bridge import MujocoBridge
from ch14_ai_interfaces.srv import SwapModel
assert numpy.__version__=='1.26.4' and torch.version.cuda is None
assert 'CPUExecutionProvider' in onnxruntime.get_available_providers()
print('G09_INSTALLED_IMPORT_PASS',numpy.__version__,torch.__version__,onnxruntime.__version__)
PY
stage=complete
