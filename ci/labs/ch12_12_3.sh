#!/usr/bin/env bash
# Ch12/docs/LAB_12_3_GUIDE_KO.md: published shortest-path MuJoCo test.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './Ch12[test,visual]'
export MUJOCO_GL=egl
python -m pytest Ch12/tests/test_locomotion_env.py \
  -q --junitxml=ci-results/Ch12/12.3/junit.xml
quadruped-rl --section 12.3 --policy stand \
  --command 0 0 0 --steps 1000 \
  | tee ci-results/Ch12/12.3/stand.log
quadruped-rl --section 12.3 --policy random \
  --command .5 .2 .3 --steps 1000 \
  | tee ci-results/Ch12/12.3/random.log
echo "CH12_12_3_MUJOCO_SMOKE_PASS"
