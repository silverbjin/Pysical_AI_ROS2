#!/usr/bin/env bash
set -Eeuo pipefail
out="$1"
export DEBIAN_FRONTEND=noninteractive PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg MUJOCO_GL=egl
apt-get update -qq
apt-get install -y --no-install-recommends python3-venv python3-pip libgl1 libegl1 libglfw3 ros-jazzy-nav-msgs ros-jazzy-sensor-msgs ros-jazzy-geometry-msgs ros-jazzy-std-msgs >/dev/null
python3 -m venv --system-site-packages /tmp/g07-venv
source /tmp/g07-venv/bin/activate
set +u
source /opt/ros/jazzy/setup.bash
set -u
lock=/ch14/requirements/cpu.lock.txt
mkdir -p /wheelhouse
if ! python -m pip download --no-index --find-links /wheelhouse --require-hashes --no-deps --only-binary=:all: -d /wheelhouse -r "$lock"; then
 grep -E '^torch(vision)?==' "$lock" >/tmp/torch.lock
 python -m pip download --require-hashes --no-deps --only-binary=:all: --index-url https://download.pytorch.org/whl/cpu -d /wheelhouse -r /tmp/torch.lock
 python -m pip download --require-hashes --no-deps --only-binary=:all: --find-links /wheelhouse -d /wheelhouse -r "$lock"
fi
python -m pip install --ignore-installed --no-deps --no-index --find-links /wheelhouse --require-hashes -r "$lock"
grep -E '^[a-zA-Z0-9_.-]+==' "$lock" | sed 's/ .*//' >/tmp/cpu-constraints.txt
if [[ -f /ch14/requirements/rl.lock.txt ]];then
 python -m pip install --no-deps --require-hashes --only-binary=:all: -r /ch14/requirements/rl.lock.txt
else
 python -m pip install --only-binary=:all: -c /tmp/cpu-constraints.txt -r /ch14/requirements/rl.in --report "$out/rl-install-report.json"
fi
python -m pip check
cp -a /ch14/vendor/ch12 /tmp/ch12-source
python -m pip install --no-deps --no-build-isolation /tmp/ch12-source
python -m pip check
python -m pip freeze --all > "$out/pip-freeze.txt"
python -c 'import torch,onnx,onnxruntime,stable_baselines3,mujoco,gymnasium,rclpy; print(torch.__version__,stable_baselines3.__version__,mujoco.__version__,gymnasium.__version__)'
python - <<'PY'
import json,hashlib,pathlib
root=pathlib.Path('/ch14')
m=json.loads((root/'vendor/ch12/REUSE_MANIFEST.json').read_text())
for row in m['files']:
    b=(root/row['target'].removeprefix('Ch14/')).read_bytes()
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['git_blob'],row
print('CH12_REUSE_BLOBS_VERIFIED',len(m['files']))
PY
