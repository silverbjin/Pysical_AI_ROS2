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
phase=BT_EXACT_PACKAGE_AVAILABILITY
bash /work/feature/Ch15/scripts/prepare_t10_bt_apt.sh "$e"
phase=NAV2_HISTORICAL_PARITY
# One evidence-driven physical candidate: restore historical Nav2 family,
# not the full host, no changes to controller parameters or contact guard.
cat > /etc/apt/preferences.d/ch15-t10-nav2-parity <<'PREF'
Package: ros-jazzy-nav2-* ros-jazzy-navigation2
Pin: version 1.3.13-*
Pin-Priority: 1001
PREF
historical=/work/native/Ch13/evidence/section_13_5_reuse/r5_preflight_20261103_v2/nav2_packages.txt
test -s "$historical"
# Precheck all 1.3.13 entries from original R5 environment receipt.
while read -r pkg ver; do
  [[ "$ver" == 1.3.13-* ]] || continue
  candidate="$(apt-cache policy "$pkg" | awk '/Candidate:/ {print $2}')"
  printf '%s expected=%s candidate=%s\n' "$pkg" "$ver" "$candidate"
  test "$candidate" = "$ver"
done < "$historical" | tee "$e/nav2-parity-candidates.txt"
candidate="$(apt-cache policy ros-jazzy-navigation2 | awk '/Candidate:/ {print $2}')"
[[ "$candidate" == 1.3.13-* ]]
phase=APT_DEPENDENCIES
# Original prepare_bt_deps.sh still verifies all five downloaded packages.
apt-get install -y --no-install-recommends git curl build-essential cmake binutils \
 python3-venv python3-pip python3-colcon-common-extensions python3-pytest \
 python3-numpy python3-scipy libssl-dev libegl1 libegl-mesa0 libgl1-mesa-dri libglfw3 libglx-mesa0 libosmesa6 \
 ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-tf2-tools \
 ros-jazzy-moveit ros-jazzy-moveit-py ros-jazzy-moveit-msgs ros-jazzy-trac-ik-kinematics-plugin \
 ros-jazzy-rosbag2 ros-jazzy-rosbag2-storage-mcap ros-jazzy-rmw-fastrtps-cpp
dpkg-query -W > "$e/dpkg-versions.txt"
phase=NAV2_INSTALLED_PARITY
/usr/bin/python3 - "$historical" "$e/dpkg-versions.txt" <<'PY' | tee "$e/nav2-parity-installed.txt"
import sys
from pathlib import Path
expected=dict(line.split() for line in Path(sys.argv[1]).read_text().splitlines() if line.strip())
installed=dict(line.split() for line in Path(sys.argv[2]).read_text().splitlines() if line.strip())
required={"ros-jazzy-nav2-controller","ros-jazzy-nav2-smac-planner","ros-jazzy-nav2-regulated-pure-pursuit-controller","ros-jazzy-nav2-bringup","ros-jazzy-nav2-planner","ros-jazzy-nav2-velocity-smoother","ros-jazzy-nav2-bt-navigator","ros-jazzy-nav2-costmap-2d"}
assert required <= installed.keys()
for name,version in installed.items():
    if name=="ros-jazzy-navigation2" or (name.startswith("ros-jazzy-nav2-") and name in expected and expected[name].startswith("1.3.13-")):
        assert version.startswith("1.3.13-"), (name,version)
        if name in expected: assert version==expected[name], (name,version,expected[name])
        print(name,version)
print("NAV2_HISTORICAL_PACKAGE_PARITY_PASS")
PY
phase=PINNED_VENV
# The ROS Docker image can export ROS site-packages through PYTHONPATH.
# Keep the pinned pip environment closed; native env.sh later adds ROS and
# the original sitecustomize appends Ubuntu dist-packages for actual execution.
printf 'inherited_PYTHONPATH=%s\n' "${PYTHONPATH:-}" > "$e/python-boundary.txt"
env -u PYTHONPATH -u PYTHONHOME /usr/bin/python3 -m venv "$CH13_REUSE_VENV"
py="$CH13_REUSE_VENV/bin/python"
isolated() { env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 "$py" "$@"; }
isolated -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.9.0+cpu'
isolated -m pip install -r /work/native/Ch13/evidence/section_13_5_reuse/r0-20261102/pip-freeze.txt
isolated -m pip freeze > "$e/pip-versions.txt"
isolated -m pip check | tee "$e/pip-check.log"
isolated - <<'PY' | tee -a "$e/python-boundary.txt"
import sys, importlib.metadata as md
from pathlib import Path
print("isolated sys.path:", sys.path)
assert sys.prefix != sys.base_prefix
assert not any(p.startswith("/opt/ros/") or p.startswith("/usr/lib/python3/dist-packages") for p in sys.path)
assert all(Path(d.locate_file("")).resolve().is_relative_to(Path(sys.prefix).resolve()) for d in md.distributions())
print("ISOLATED_PIP_BOUNDARY_PASS")
PY
/usr/bin/python3 - <<'PY' | tee -a "$e/python-boundary.txt"
import typeguard, yaml
print("system typeguard",typeguard.__file__,"yaml",yaml.__file__)
assert typeguard.__file__.startswith("/usr/lib/python3/dist-packages/")
print("SYSTEM_APT_IMPORT_PASS")
PY
MUJOCO_GL=egl isolated - <<'PY' | tee "$e/runtime-imports.log"
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
if [[ "${1:-}" == --table-mission ]]; then
  phase=TABLE_BASIC_BT_MCAP
  export CMAKE_BUILD_PARALLEL_LEVEL=2
  bash /work/feature/Ch15/scripts/run_table_mission.sh /work/native /work/feature/Ch15/dependencies/native_local_use_approval.json "$e/case"
  python3 - "$e/case/native/basic_result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['source']=='CH15_TABLE_V3_BT' and r['result']=='PASS'
assert len(r['checks'])==10 and all(r['checks'].values())
assert r['original_native_l2_pass'] is False and r['full_mission_success'] is False
assert r['actual_table_segment']=='PASS' and all(r['segment_checks'].values())
assert r['original_basic_assessor_result']=='PASS' and r['independent_engine_audit']=='PASS' and r['session_contract'] is True and r['exact_goal_trace'] is True
print('CH15_TABLE_BASIC_L2_PASS_10_OF_10')
PY
  phase=COMPLETE
  exit 0
fi
if [[ "${1:-}" == --table-segment ]]; then
  phase=TABLE_SEGMENT
  export CMAKE_BUILD_PARALLEL_LEVEL=2
  bash /work/feature/Ch15/scripts/run_table_segment.sh /work/native /work/feature/Ch15/dependencies/native_local_use_approval.json "$e/case"
  python3 - "$e/case/native/segment_result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['source']=='CH15_TABLE_V3_SEGMENT_V5' and r['result']=='PASS_SCOPED_TABLE_SEGMENT'
assert not r['original_native_l2_pass'] and not r['full_mission_success']
assert len(r['phases'])==4 and all(r['checks'].values())
assert all(p['terminal']==4 and p['settled'] for p in r['phases'][:2])
assert all(p['ready'] for p in r['phases'][2:])
assert r['handoff']['owner']=='V3' and r['mux']['nav2_packets']>0 and r['mux']['v3_packets']>0
print('CH15_TABLE_SEGMENT_PASS')
PY
  phase=COMPLETE
  exit 0
fi
if [[ "${1:-}" == --arc-straight ]]; then
  phase=ISOLATED_ARC_STRAIGHT
  export CMAKE_BUILD_PARALLEL_LEVEL=2
  bash /work/feature/Ch15/scripts/run_arc_straight_qualification.sh /work/native /work/feature/Ch15/dependencies/native_local_use_approval.json "$e/case"
  python3 - "$e/case/native/arc_straight_result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['source']=='CH15_COUPLED_ARC_STRAIGHT_V3' and r['result']=='PASS_SCOPED_ARC_STRAIGHT'
assert not r['original_native_l2_pass'] and not r['segment_pass'] and not r['full_mission_success']
assert len(r['phases'])==2 and all(p['ready'] for p in r['phases'])
assert all(r['checks'].values())
print('CH15_COUPLED_ARC_STRAIGHT_PASS')
PY
  phase=COMPLETE
  exit 0
fi
if [[ "${1:-}" == --plant-identification ]]; then
  phase=ISOLATED_PLANT_IDENTIFICATION
  export CMAKE_BUILD_PARALLEL_LEVEL=2
  bash /work/feature/Ch15/scripts/run_plant_identification.sh /work/native /work/feature/Ch15/dependencies/native_local_use_approval.json "$e/case"
  python3 - "$e/case/native/plant_result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['result']=='PASS_SCOPED_IDENTIFICATION'
assert r['source']=='CH15_ISOLATED_PLANT_IDENTIFICATION_V1'
assert not r['original_native_l2_pass'] and not r['segment_pass'] and not r['full_mission_success']
assert len(r['phases'])==3 and all(r['checks'].values())
print('CH15_PLANT_IDENTIFICATION_PASS')
PY
  phase=COMPLETE
  exit 0
fi
if [[ "${1:-}" == --heading-segment ]]; then
  phase=HEADING_FIRST_SEGMENT
  export CMAKE_BUILD_PARALLEL_LEVEL=2
  bash /work/feature/Ch15/scripts/run_heading_first_segment.sh /work/native /work/feature/Ch15/dependencies/native_local_use_approval.json "$e/case"
  phase=SEGMENT_RESULT_VERIFICATION
  python3 - "$e/case/native/segment_result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['result']=='PASS_SCOPED_SEGMENT' and r['source']=='CH15_HEADING_FIRST_V2'
assert r['original_native_l2_pass'] is False and r['full_mission_success'] is False
assert set(r['checks'])=={'stage_aligned','straight_map_clear','final_pose','fresh_final_observation','workspace','one_command_chain','no_fault','engine_clean','children_clean'}
assert all(r['checks'].values()) and len(r['phases'])==3
assert all(p['terminal']==4 and p['settled'] for p in r['phases'])
print("CH15_HEADING_FIRST_SEGMENT_PASS")
PY
  phase=COMPLETE
  exit 0
fi
phase=NATIVE_BUILD_INSTALL_AND_LEVEL2
# Original runner owns all commands, shutdown and assessment. No alternate path.
# Isolate build parallelism only, not runtime control parameters.
export CMAKE_BUILD_PARALLEL_LEVEL=2
if bash /work/feature/Ch15/scripts/run_physical_basic.sh /work/native /work/feature/Ch15/dependencies/native_local_use_approval.json "$e/case"; then
  :
else
  rc=$?
  if [[ -f "$e/case/build.log" ]]; then tail -n 100 "$e/case/build.log"; fi
  exit "$rc"
fi
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
