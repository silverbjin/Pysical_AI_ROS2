#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=init
trap 'rc=$?; printf "{\"status\":\"%s\",\"stage\":\"%s\",\"exit_code\":%d,\"scope\":\"G04_CPU_RUNTIME_CONFIGURATION\"}\n" "$(if ((rc==0)); then echo PASS; else echo FAIL; fi)" "$stage" "$rc" > "$out/result.json"' EXIT
export DEBIAN_FRONTEND=noninteractive PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg YOLO_CONFIG_DIR=/tmp/ch14-ultralytics
export ROS_DOMAIN_ID=73 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST GZ_IP=127.0.0.1 GZ_PARTITION="ch14_g04_${GITHUB_RUN_ID:-local}_$$"
export QT_QPA_PLATFORM=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
unset DISPLAY
stage=environment
apt-get update -qq
apt-get install -y --no-install-recommends python3-venv python3-pip ros-jazzy-cv-bridge ros-jazzy-vision-msgs ros-jazzy-message-filters ros-jazzy-tf2-ros-py ros-jazzy-diagnostic-msgs ros-jazzy-rosgraph-msgs ros-jazzy-ros-gz-bridge ros-jazzy-ros-gz-sim ros-jazzy-tf2-ros ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-ament-cmake >/dev/null
python3 -m venv --system-site-packages /tmp/ch14-venv
source /tmp/ch14-venv/bin/activate
set +u
source /opt/ros/jazzy/setup.bash
set -u
lock=/ch14/requirements/cpu.lock.txt
# Exact cache from successful G00; fallback to pinned downloads only on missing wheels.
if ! python -m pip download --no-index --find-links /wheelhouse --require-hashes --no-deps --only-binary=:all: -d /wheelhouse -r "$lock"; then
 grep -E '^torch(vision)?==' "$lock" >/tmp/torch.lock
 python -m pip download --require-hashes --no-deps --only-binary=:all: --index-url https://download.pytorch.org/whl/cpu -d /wheelhouse -r /tmp/torch.lock
 python -m pip download --require-hashes --no-deps --only-binary=:all: --find-links /wheelhouse -d /wheelhouse -r "$lock"
fi
python /ch14/scripts/g00_make_wheel_lock.py /wheelhouse "$out"
cmp "$lock" "$out/cpu.candidate.lock.txt"
python -m pip install --ignore-installed --no-deps --no-index --find-links /wheelhouse --require-hashes -r "$lock"
python -m pip check
export PYTHONPATH=/ch14/ros2_ws/src/ch14_ai_common:${PYTHONPATH:-}
stage=core
cd /ch14
export PYTHONPATH=/ch14/ros2_ws/src/ch14_ai_perception:$PYTHONPATH
python -m pytest -q -p no:cacheprovider tests/test_g04_contracts.py tests/test_g03_core.py --junitxml="$out/core-tests.xml"
stage=colcon
mkdir -p /tmp/ch14-build/src
cp -a /ch14/ros2_ws/src/{ch14_ai_common,ch14_ai_interfaces,ch14_ai_perception,ch14_simulation} /tmp/ch14-build/src/
cd /tmp/ch14-build
python "$(command -v colcon)" build --packages-select ch14_ai_common ch14_ai_interfaces ch14_ai_perception ch14_simulation --cmake-args -DPython3_EXECUTABLE="$(command -v python)" 2>&1 | tee "$out/colcon-build.log"
unset PYTHONPATH
set +u
source /opt/ros/jazzy/setup.bash
source /tmp/ch14-build/install/setup.bash
set -u
ros2 interface show ch14_ai_interfaces/srv/SwapModel | tee "$out/service-type.txt"
ros2 launch ch14_ai_perception robot_ai_system.launch.py --show-args > "$out/launch-args.txt"
stage=registry
cd /ch14
for id in yolov8n yolov8s; do
 python scripts/fetch_models.py "$id" --cache /tmp/models --fetch --acknowledge-agpl
done
python scripts/g04_prepare_registry.py --cache /tmp/models --output /tmp/registry --manifest models/model_manifest.json --receipt "$out/registry-receipt.json"
stage=candidate_negative
python scripts/g04_candidate_negative.py /tmp/registry/registry.json "$out/candidate-negative.json"
stage=replay
python scripts/g04_actual_probe.py --registry /tmp/registry/registry.json --image /fixture/000000455085.jpg --out "$out"
stage=sim
export ROS_DOMAIN_ID=74
python scripts/g04_sim_launch_probe.py --registry /tmp/registry/registry.json --assets /assets --out "$out"
stage=complete
