#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=init
trap 'rc=$?; printf "{\"status\":\"%s\",\"stage\":\"%s\",\"exit_code\":%d}\n" "$(if ((rc==0)); then echo PASS; else echo FAIL; fi)" "$stage" "$rc" > "$out/result.json"' EXIT
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
export PYTHONPATH=/ch14/ros2_ws/src/ch14_ai_common:$PYTHONPATH
stage=regression
cd /ch14
python -m pytest -q -p no:cacheprovider tests/test_g01_yolo_contract.py
stage=asset_acquisition
# User requested actual model evaluation. AGPL acknowledged as source license, NOT release approval.
# Weights and images remain in disposable container. Never upload them or exported ONNX.
for id in yolov8n yolov8s; do
 python scripts/fetch_models.py "$id" --cache /tmp/models --fetch --acknowledge-agpl
done
stage=T01
for threads in 1 2; do
 python python/benchmark_torch.py --manifest models/model_manifest.json --cache /tmp/models --model yolov8n --threads "$threads" --output "$out/t01_threads_$threads"
done
stage=T02
# Export each model once; T04 consumes the exact same exported bytes.
for id in yolov8n yolov8s; do
 python python/export_yolo.py --manifest models/model_manifest.json --cache /tmp/models --model "$id" --output "/tmp/$id"
 cp "/tmp/$id/export.json" "$out/$id-export.json"
done
stage=fixture_candidate
python scripts/g01_select_coco.py /tmp/coco
cp /tmp/coco/manifest.json "$out/fixture-candidate.json"
stage=T04
python - "$out" <<'PY'
import json,sys
from pathlib import Path
from ch14_ai_common.backends import TorchBackend,OrtBackend
from ch14_ai_common.yolo_lab import compare_images,read_fixture,infer_image
out=Path(sys.argv[1]);failed=False
for mid in ('yolov8n','yolov8s'):
    meta=json.loads((out/f'{mid}-export.json').read_text())
    model=Path('/tmp')/mid/f'{mid}.onnx'
    pt=TorchBackend(Path('/tmp/models')/f'{mid}.pt',meta['source_sha256'])
    ort=OrtBackend(model,meta['onnx_sha256'])
    rows=list(read_fixture(Path('/tmp/coco/manifest.json'),Path('/tmp/coco/images')))
    r=compare_images(pt,ort,rows,out/f'{mid}-parity.json')
    infer_image(ort,Path('/tmp/coco/images')/rows[0][0]['file'],Path('/tmp')/f'{mid}-sample')
    # Annotation images not redistributed; JSON detection evidence only.
    import shutil
    shutil.copyfile(Path('/tmp')/f'{mid}-sample/detections.json',out/f'{mid}-sample-detections.json')
    failed |= r['status']!='PASS'
if failed:raise SystemExit('T04 parity/target failed; no threshold relaxation')
PY
stage=complete
