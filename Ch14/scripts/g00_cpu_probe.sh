#!/usr/bin/env bash
set -Eeuo pipefail
out="$(realpath "$1")"
mkdir -p "$out"
stage=init
trap 'rc=$?; printf "{\"gate\":\"G00\",\"scope\":\"CPU_PROFILE_PREFLIGHT\",\"stage\":\"%s\",\"exit_code\":%s,\"status\":\"%s\"}\n" "$stage" "$rc" "$(if ((rc==0)); then echo PASS; else echo FAIL; fi)" > "$out/result.json"' EXIT
step() { stage="$1"; printf 'G00_STAGE=%s\n' "$stage"; }
export DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONNOUSERSITE=1 YOLO_CONFIG_DIR=/tmp/ch14-ultralytics MPLBACKEND=Agg OMP_NUM_THREADS=1
step apt
cat /etc/os-release > "$out/os-release.txt"
apt-get update
apt-get install -y --no-install-recommends python3-venv python3-pip ros-jazzy-cv-bridge ros-jazzy-vision-msgs
dpkg-query -W > "$out/dpkg-versions.txt"
step venv
python3 -m venv --system-site-packages /tmp/ch14-venv
source /tmp/ch14-venv/bin/activate
set +u
source /opt/ros/jazzy/setup.bash
set -u
python -V
python -m pip --version
python -m pip inspect > "$out/system-pip-inspect.json"
python -m pip check > "$out/system-pip-check.txt"
wh=/wheelhouse
mkdir -p "$wh"
lock=/ch14/requirements/cpu.ros-probe.lock.txt
step download_cpu_torch
grep -E '^torch(vision)?==' "$lock" > /tmp/ch14-torch.lock.txt
python -m pip download --require-hashes --only-binary=:all: --no-deps --index-url https://download.pytorch.org/whl/cpu --dest "$wh" -r /tmp/ch14-torch.lock.txt
step download_pinned_wheels
python -m pip download --require-hashes --only-binary=:all: --no-deps --index-url https://pypi.org/simple --find-links "$wh" --dest "$wh" -r "$lock"
step hash_lock
python /ch14/scripts/g00_make_wheel_lock.py "$wh" "$out"
cmp "$lock" "$out/cpu.candidate.lock.txt"
touch "$out/wheelhouse-verified"
step graph_before_install
python /ch14/scripts/validate_dependency_graph.py "$out/system-pip-inspect.json" "$wh" "$out/dependency-graph.json"
step install_locked
# The complete overlay is explicit; inherited ROS tooling is validated above and below.
python -m pip install --ignore-installed --no-deps --no-index --find-links "$wh" --require-hashes -r "$lock"
python -m pip freeze --all > "$out/pip-freeze.txt"
python -m pip inspect > "$out/effective-pip-inspect.json"
step pip_check
python -m pip check | tee "$out/pip-check.txt"
step installed_graph
mkdir -p /tmp/ch14-empty-wheels
python /ch14/scripts/validate_dependency_graph.py "$out/effective-pip-inspect.json" /tmp/ch14-empty-wheels "$out/installed-graph.json"
python - "$out/dependency-graph.json" "$out/installed-graph.json" <<'PY'
import json, sys
a,b=(json.load(open(p))['effective'] for p in sys.argv[1:])
for k,v in a.items():
    if k not in b or v['version'] != b[k]['version']:
        raise SystemExit(f'Effective distribution drift: {k}: {v["version"]} -> {b.get(k)}')
print('EFFECTIVE_GRAPH_VERSION_MATCH', len(a))
PY
step colcon_build
mkdir -p /tmp/ch14-build/src
cp -a /ch14/ros2_ws/src/ch14_ai_common /tmp/ch14-build/src/
cd /tmp/ch14-build
python "$(command -v colcon)" build --packages-select ch14_ai_common 2>&1 | tee "$out/colcon-build.log"
set +u
source /tmp/ch14-build/install/setup.bash
set -u
python -c 'import ch14_ai_common; print(ch14_ai_common.__file__)'
step abi_export_smoke
python /ch14/scripts/g00_cpu_smoke.py "$out"
step complete
