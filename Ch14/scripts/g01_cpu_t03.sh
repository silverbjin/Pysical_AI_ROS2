#!/usr/bin/env bash
set -Eeuo pipefail
out="$1"
mkdir -p "$out"
source /tmp/ch14-venv/bin/activate
set +u
source /opt/ros/jazzy/setup.bash
source /tmp/ch14-build/install/setup.bash
set -u
export PYTHONNOUSERSITE=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg
cd /ch14
python -m pytest -q -p no:cacheprovider tests/test_g01_foundation.py | tee "$out/foundation.log"
python /ch14/python/export_custom_model.py --output "$out/t03" | tee "$out/t03.log"
