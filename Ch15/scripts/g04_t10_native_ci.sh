#!/usr/bin/env bash
# Dedicated Linux CI container only; never use a shared owner installation.
set -Eeuo pipefail
cd /work
e=/work/t10-evidence
mkdir -p "$e"
phase=ENVIRONMENT
finish() {
  rc=$?
  printf '{"phase":"%s","exit":%d}\n' "$phase" "$rc" > "$e/phase-exit.json"
}
trap finish EXIT
exec > >(tee "$e/container.log") 2>&1
export DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
export CH13_REUSE_BUILD=/work/ch13_reuse_13_8_build
export CH13_REUSE_VENV=/work/ch13_reuse_iit_d010212_venv
test ! -e "$CH13_REUSE_BUILD"
test ! -e "$CH13_REUSE_VENV"
. /etc/os-release
test "$VERSION_ID" = 24.04
test "$(uname -m)" = x86_64
test -f /opt/ros/jazzy/setup.bash
cat /etc/os-release > "$e/os-release.txt"
nproc > "$e/cores.txt"
free -h > "$e/memory.txt"
df -h /work > "$e/disk.txt"
git config --global --add safe.directory /work/native
git config --global --add safe.directory /work/feature
phase=APT_DEPENDENCIES
apt-get update
# Original guide's build/runtime dependencies; BT deb bytes are checked by
# original prepare_bt_deps.sh, not replaced with newer packages.
apt-cache policy ros-jazzy-py-trees ros-jazzy-py-trees-ros ros-jazzy-py-trees-ros-interfaces python3-pydot python3-pyparsing > "$e/bt-apt-policy.txt"
apt-get install -y --no-install-recommends git curl build-essential cmake binutils \
 python3-venv python3-pip python3-colcon-common-extensions python3-pytest \
 python3-numpy python3-scipy libssl-dev libegl1 libegl-mesa0 libgl1-mesa-dri libglfw3 libglx-mesa0 libosmesa6 \
 ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-tf2-tools \
 ros-jazzy-moveit ros-jazzy-moveit-py ros-jazzy-moveit-msgs ros-jazzy-trac-ik-kinematics-plugin \
 ros-jazzy-rosbag2 ros-jazzy-rosbag2-storage-mcap ros-jazzy-rmw-fastrtps-cpp
dpkg-query -W > "$e/dpkg-versions.txt"
phase=PINNED_VENV
python3 -m venv "$CH13_REUSE_VENV"
py="$CH13_REUSE_VENV/bin/python"
"$py" -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.9.0+cpu'
"$py" -m pip install -r /work/native/Ch13/evidence/section_13_5_reuse/r0-20261102/pip-freeze.txt
"$py" -m pip check
"$py" -m pip freeze > "$e/pip-versions.txt"
MUJOCO_GL=egl "$py" - <<'PY' | tee "$e/runtime-imports.log"
import sys, mujoco, torch, onnxruntime, numpy
print(sys.version)
print("mujoco",mujoco.__version__,"torch",torch.__version__,"ort",onnxruntime.__version__,"numpy",numpy.__version__)
assert mujoco.__version__=="3.13.0" and torch.__version__=="2.9.0+cpu"
m=mujoco.MjModel.from_xml_string('<mujoco><worldbody><light pos="0 0 3"/><geom type="plane" size="1 1 .1"/></worldbody></mujoco>')
d=mujoco.MjData(m)
with mujoco.Renderer(m,height=32,width=32) as r:
    r.update_scene(d)
    assert r.render().shape==(32,32,3)
print("EGL_RENDER_SMOKE_PASS")
PY
phase=ASSET_MATERIALIZATION
# New ephemeral workspace: reconstruct same bytes using already verified method.
# No historical audit repetition and no asset upload.
python3 /work/feature/Ch15/scripts/prepare_native_assets.py --target /work/upstream-iit-locomanipulation-d010212 --receipt "$e/asset-verification.json" > "$e/acquisition.log"
touch /work/ch13_reuse_engine.lock
phase=NATIVE_BUILD_INSTALL_AND_LEVEL2
# Original runner owns all commands, shutdown and assessment. No alternate path.
# Isolate build parallelism only, not runtime control parameters.
export CMAKE_BUILD_PARALLEL_LEVEL=2
bash /work/feature/Ch15/scripts/run_physical_basic.sh /work/native /work/feature/Ch15/dependencies/native_local_use_approval.json "$e/case"
phase=RESULT_VERIFICATION
python3 - "$e/case/result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r["result"]=="PASS" and r["source"]=="CH13_NATIVE"
assert len(r["checks"])==10 and all(v is True for v in r["checks"].values())
assert r["full_mission_success"] is False
print("CH15_T10_NATIVE_LEVEL2_PASS_10_OF_10")
PY
phase=COMPLETE
