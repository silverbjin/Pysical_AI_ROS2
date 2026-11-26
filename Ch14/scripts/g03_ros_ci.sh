#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=init
trap 'rc=$?; printf "{\"status\":\"%s\",\"stage\":\"%s\",\"exit_code\":%d,\"scope\":\"G03_L0_L1_REPLAY_ONLY\"}\n" "$(if ((rc==0)); then echo PASS; else echo FAIL; fi)" "$stage" "$rc" > "$out/result.json"' EXIT
export DEBIAN_FRONTEND=noninteractive PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg YOLO_CONFIG_DIR=/tmp/ch14-ultralytics ROS_DOMAIN_ID=71 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
stage=environment
apt-get update -qq
apt-get install -y --no-install-recommends python3-venv python3-pip ros-jazzy-cv-bridge ros-jazzy-vision-msgs ros-jazzy-message-filters ros-jazzy-tf2-ros-py ros-jazzy-diagnostic-msgs ros-jazzy-rosgraph-msgs ros-jazzy-rosidl-default-generators ros-jazzy-rosidl-default-runtime ros-jazzy-ament-cmake >/dev/null
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
stage=core_test
cd /ch14
export PYTHONPATH=/ch14/ros2_ws/src/ch14_ai_perception:$PYTHONPATH
python -m pytest -q -p no:cacheprovider tests/test_g03_core.py --junitxml="$out/core-tests.xml"
stage=colcon
mkdir -p /tmp/ch14-build/src
cp -a /ch14/ros2_ws/src/ch14_ai_common /ch14/ros2_ws/src/ch14_ai_interfaces /ch14/ros2_ws/src/ch14_ai_perception /tmp/ch14-build/src/
cd /tmp/ch14-build
python "$(command -v colcon)" build --packages-select ch14_ai_common ch14_ai_interfaces ch14_ai_perception 2>&1 | tee "$out/colcon-build.log"
unset PYTHONPATH
set +u
source /opt/ros/jazzy/setup.bash
source /tmp/ch14-build/install/setup.bash
set -u
python -c 'import ch14_ai_perception, ch14_ai_common; print(ch14_ai_perception.__file__,ch14_ai_common.__file__)' | tee "$out/installed-imports.txt"
ros2 launch ch14_ai_perception perception.launch.py --show-args > "$out/launch-args.txt"
stage=asset
cd /ch14
python scripts/fetch_models.py yolov8n --cache /tmp/models --fetch --acknowledge-agpl
python python/export_yolo.py --manifest models/model_manifest.json --cache /tmp/models --model yolov8n --output /tmp/yolov8n --threads 1
cp /tmp/yolov8n/export.json "$out/yolov8n-export.json"
sha="$(python -c 'import json;print(json.load(open("/tmp/yolov8n/export.json"))["onnx_sha256"])')"
stage=dds
python scripts/g03_ros_dds_probe.py --onnx /tmp/yolov8n/yolov8n.onnx --sha256 "$sha" --image /fixture/000000455085.jpg --out "$out" --phase "${G03_PHASE:-all}"
stage=complete
