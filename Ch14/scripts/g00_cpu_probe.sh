#!/usr/bin/env bash
set -Eeuo pipefail
out="$(realpath "$1")"
mkdir -p "$out"
stage=init
trap 'rc=$?; printf "{\"gate\":\"G00\",\"scope\":\"CPU_PROFILE_PREFLIGHT\",\"stage\":\"%s\",\"exit_code\":%s,\"status\":\"%s\"}\n" "$stage" "$rc" "$(if ((rc==0)); then echo PASS; else echo FAIL; fi)" > "$out/result.json"' EXIT
export DEBIAN_FRONTEND=noninteractive
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONNOUSERSITE=1
export YOLO_CONFIG_DIR=/tmp/ch14-ultralytics
export MPLBACKEND=Agg
export OMP_NUM_THREADS=1
stage=lock_regression
python3 /ch14/scripts/test_g00_wheel_lock.py
stage=apt
cat /etc/os-release > "$out/os-release.txt"
apt-get update
apt-get install -y --no-install-recommends python3-venv python3-pip ros-jazzy-cv-bridge ros-jazzy-vision-msgs
dpkg-query -W > "$out/dpkg-versions.txt"
stage=venv
python3 -m venv --system-site-packages /tmp/ch14-venv
source /tmp/ch14-venv/bin/activate
set +u
source /opt/ros/jazzy/setup.bash
set -u
python -V
python -m pip --version
wh=/tmp/ch14-wheelhouse
mkdir -p "$wh"
stage=download_cpu_torch
python -m pip download --only-binary=:all: --no-deps --index-url https://download.pytorch.org/whl/cpu --dest "$wh" 'torch==2.5.1+cpu' 'torchvision==0.20.1+cpu'
stage=resolve
python -m pip download --only-binary=:all: --index-url https://pypi.org/simple --find-links "$wh" --dest "$wh" -r /ch14/requirements/cpu.candidate.txt
stage=hash_lock
python /ch14/scripts/g00_make_wheel_lock.py "$wh" "$out"
stage=install_locked
python -m pip install --ignore-installed --no-index --find-links "$wh" --require-hashes -r "$out/cpu.candidate.lock.txt"
python -m pip freeze --all > "$out/pip-freeze.txt"
python -m pip check
stage=abi_export_smoke
python /ch14/scripts/g00_cpu_smoke.py "$out"
stage=complete
