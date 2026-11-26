#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=init
trap 'rc=$?; printf "{\"status\":\"%s\",\"stage\":\"%s\",\"exit_code\":%d,\"scope\":\"G02_CPU_COMPARISON_ONLY\"}\n" "$(if ((rc==0)); then echo PASS; else echo FAIL; fi)" "$stage" "$rc" > "$out/result.json"' EXIT
export DEBIAN_FRONTEND=noninteractive PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg YOLO_CONFIG_DIR=/tmp/ch14-ultralytics
stage=environment
apt-get update -qq
apt-get install -y --no-install-recommends python3-venv python3-pip ros-jazzy-cv-bridge ros-jazzy-vision-msgs >/dev/null
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
stage=openvino_overlay
mkdir -p /ovwheelhouse
ovlock=/ch14/requirements/openvino.lock.txt
python -m pip download --only-binary=:all: --require-hashes --no-deps --dest /ovwheelhouse -r "$ovlock"
python /ch14/scripts/g00_make_wheel_lock.py /ovwheelhouse /tmp
sort "$ovlock" > /tmp/expected-ov.lock
sort /tmp/cpu.candidate.lock.txt > /tmp/actual-ov.lock
cmp /tmp/expected-ov.lock /tmp/actual-ov.lock
python -m pip inspect > "$out/base-pip-inspect.json"
python /ch14/scripts/validate_dependency_graph.py "$out/base-pip-inspect.json" /ovwheelhouse "$out/openvino-dependency-graph.json"
python -m pip install --no-index --find-links /ovwheelhouse --require-hashes --no-deps -r "$ovlock"
python -m pip check | tee "$out/pip-check.txt"
python -m pip inspect > "$out/effective-pip-inspect.json"
stage=regression
cd /ch14
python -m pytest -q -p no:cacheprovider tests/test_g02_comparison.py
stage=assets
cp /fixture/manifest.json "$out/fixture-manifest.json"
for id in yolov8n yolov8s; do
 python scripts/fetch_models.py "$id" --cache /tmp/models --fetch --acknowledge-agpl
done
stage=compare
failed=0
for id in yolov8n yolov8s; do
 python python/export_yolo.py --manifest models/model_manifest.json --cache /tmp/models --model "$id" --output "/tmp/$id" --threads 1
 cp "/tmp/$id/export.json" "$out/$id-export.json"
 read -r sha ptsha < <(python -c "import json;d=json.load(open('/tmp/$id/export.json'));print(d['onnx_sha256'],d['source_sha256'])")
 if [[ "$id" == yolov8n ]]; then prior=e8950e7e6edc29ee614a027ee7a07aa492afbda7f24faad049972be5b7c96546; else prior=6b213b04c58fc0df0039d59f00b665b727943ebed2a6a393727a2423a95e50e9; fi
 args=()
 if [[ "$sha" != "$prior" ]]; then args=(--pt "/tmp/models/$id.pt" --pt-sha "$ptsha"); fi
 if ! python python/compare_backends.py --onnx "/tmp/$id/$id.onnx" --sha256 "$sha" --prior-sha "$prior" --fixtures /fixture/manifest.json --images /fixture/images --threads 2 --output "$out/$id" "${args[@]}"; then failed=1; fi
done
stage=sample_cli
read -r sha < <(python -c "import json;print(json.load(open('/tmp/yolov8n/export.json'))['onnx_sha256'])")
python python/ov_inference.py --onnx /tmp/yolov8n/yolov8n.onnx --sha256 "$sha" --image /fixture/images/000000455085.jpg --output /tmp/ov-sample
cp /tmp/ov-sample/detections.json "$out/ov-sample-detections.json"
stage=acceptance
[[ "$failed" == 0 ]]
stage=complete
