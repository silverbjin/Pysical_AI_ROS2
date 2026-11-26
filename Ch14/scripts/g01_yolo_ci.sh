#!/usr/bin/env bash
set -Eeuo pipefail
out=/evidence
stage=init
trap 'rc=$?; printf "{\"status\":\"%s\",\"stage\":\"%s\",\"exit_code\":%d}\n" "$(if ((rc==0)); then echo PASS; else echo FAIL; fi)" "$stage" "$rc" > "$out/result.json"' EXIT
export DEBIAN_FRONTEND=noninteractive PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg YOLO_CONFIG_DIR=/tmp/ch14-ultralytics
stage=fixture_preflight
[[ -f /fixture/manifest.json ]]
cp /fixture/manifest.json "$out/fixture-candidate.json"
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
stage=prior_evidence
# Reuse only source-identical T01/T02; exact prior evidence remains immutable.
if python scripts/g01_check_reuse.py evidence/g01_run_45744146299.json "$out/t01-t02-reuse.json"; then
  reuse=1
else
  reuse=0
fi
stage=T01
if [[ "$reuse" == 0 ]]; then
 for threads in 1 2; do
  python python/benchmark_torch.py --manifest models/model_manifest.json --cache /tmp/models --model yolov8n --threads "$threads" --output "$out/t01_threads_$threads"
 done
else
 echo T01_REUSED_RUN_45744146299
fi
stage=T02
# Export each model once; T04 consumes the exact same exported bytes.
for id in yolov8n yolov8s; do
 python python/export_yolo.py --manifest models/model_manifest.json --cache /tmp/models --model "$id" --output "/tmp/$id"
 cp "/tmp/$id/export.json" "$out/$id-export.json"
done
if [[ "$reuse" == 1 ]]; then
 python scripts/g01_check_reuse.py evidence/g01_run_45744146299.json "$out/t01-t02-reuse.json" --exports "$out"
fi
stage=T04
python - "$out" <<'PY'
import json,sys
from pathlib import Path
from ch14_ai_common.backends import TorchBackend,OrtBackend
from ch14_ai_common.yolo_lab import compare_images,read_fixture,infer_image
import torch,subprocess
out=Path(sys.argv[1]);failed=False
for mid in ('yolov8n','yolov8s'):
    meta=json.loads((out/f'{mid}-export.json').read_text())
    model=Path('/tmp')/mid/f'{mid}.onnx'
    pt_path=Path('/tmp/models')/f'{mid}.pt'
    pt=TorchBackend(pt_path,meta['source_sha256'])
    ort=OrtBackend(model,meta['onnx_sha256'])
    # Actual fail-closed boundary checks on pinned model/CPU runtime.
    def rejected(fn, types):
        try: fn()
        except types: return True
        raise AssertionError('invalid input not rejected')
    checks={
      'missing_onnx':rejected(lambda:OrtBackend(Path('/tmp/nonexistent-ch14.onnx'),meta['onnx_sha256']), (ValueError,FileNotFoundError)),
      'wrong_onnx_sha':rejected(lambda:OrtBackend(model,'0'*64),(ValueError,)),
      'wrong_pt_sha':rejected(lambda:TorchBackend(pt_path,'0'*64),(ValueError,)),
      'missing_image':rejected(lambda:infer_image(ort,Path('/tmp/nonexistent-ch14.jpg'),Path('/tmp/invalid-output')),(ValueError,))}
    if not torch.cuda.is_available(): checks['cuda_unavailable_rejected']=rejected(lambda:TorchBackend(pt_path,meta['source_sha256'],'cuda'),(RuntimeError,))
    (out/f'{mid}-negative-contracts.json').write_text(json.dumps(checks,indent=2)+'\n')
    rows=list(read_fixture(Path('/fixture/manifest.json'),Path('/fixture/images')))
    r=compare_images(pt,ort,rows,out/f'{mid}-parity.json')
    subprocess.run([sys.executable,'python/inference_onnx.py','--onnx',str(model),'--sha256',meta['onnx_sha256'], '--image',str(Path('/fixture/images')/rows[0][0]['file']),'--output',str(Path('/tmp')/f'{mid}-sample')],check=True)
    # Annotation images not redistributed; JSON detection evidence only.
    import shutil
    shutil.copyfile(Path('/tmp')/f'{mid}-sample/detections.json',out/f'{mid}-sample-detections.json')
    failed |= r['status']!='PASS'
(out/"t04-status.json").write_text(json.dumps({"status":"FAIL" if failed else "PASS"})+"\n")
PY
stage=label_metrics
python scripts/g01_label_metrics.py "$out/fixture-candidate.json" "$out"
stage=T04_acceptance
python - "$out/t04-status.json" <<'PY'
import json,sys
if json.load(open(sys.argv[1]))["status"]!="PASS":
    raise SystemExit("T04 parity/target failed; no threshold relaxation")
PY
stage=complete
