#!/usr/bin/env bash
# Ch01 §1.7: genuine colcon installation of textbook package and added
# launch/config data_files in an isolated source copy. No old lab retest.
set -Eeuo pipefail
set +u; source /opt/ros/jazzy/setup.bash; set -u
ROOT=/work
OUT="$ROOT/ci-results/ch01-17"
mkdir -p "$OUT"
ORIGINAL="$ROOT/Ch01/robot_ws/src/my_robot_controller"
TMP="$(mktemp -d /tmp/book_ch01_17.XXXXXXXX)"
STAGE=INIT
stage() { STAGE="$1"; echo "STAGE=$1" | tee -a "$OUT/stages.log"; }
cleanup() {
  rc="$?"; trap - EXIT; set +e
  if [[ -d "$TMP" ]]; then rm -rf "$TMP"; fi
  printf '{"chapter":"Ch01","section":"1.7","last_stage":"%s","exit_code":%d,"whole_chapter_accepted":false,"ch10":"HOLD"}\n' \
    "$STAGE" "$rc" > "$OUT/exit.json"
  exit "$rc"
}
trap cleanup EXIT

stage COPY_ORIGINAL_PACKAGE_WITH_NO_SOURCE_EDIT
test -f "$ORIGINAL/setup.py"
sha256sum "$ORIGINAL/setup.py" | tee "$OUT/original_setup_sha_before.txt"
mkdir -p "$TMP/ws/src"
cp -a "$ORIGINAL" "$TMP/ws/src/my_robot_controller"
PKG="$TMP/ws/src/my_robot_controller"
mkdir -p "$PKG/launch" "$PKG/config"
cat > "$PKG/launch/asset_demo.launch.py" <<'PY'
from launch import LaunchDescription
from launch.actions import LogInfo

def generate_launch_description():
    return LaunchDescription([LogInfo(msg="CH01_17_ACTUAL_INSTALLED_LAUNCH_DISCOVERED")])
PY
cat > "$PKG/config/lesson.yaml" <<'YAML'
lesson: "Ch01 Section 1.7"
purpose: "ament_python data_files installation"
hardware_command: false
YAML
python3 - "$PKG/setup.py" <<'PY'
from pathlib import Path
import sys
f=Path(sys.argv[1])
s=f.read_text()
needle="        ('share/' + package_name, ['package.xml']),"
assert s.count(needle)==1
assert "asset_demo.launch.py" not in s
s=s.replace(needle,needle+"""
        ('share/' + package_name + '/launch', ['launch/asset_demo.launch.py']),
        ('share/' + package_name + '/config', ['config/lesson.yaml']),""")
f.write_text(s)
compile(s,str(f),"exec")
print("CH01_17_COPY_ONLY_SETUP_ASSET_RULES_ADDED",flush=True)
PY
sha256sum "$ORIGINAL/setup.py" | tee "$OUT/original_setup_sha_after.txt"
cmp "$OUT/original_setup_sha_before.txt" "$OUT/original_setup_sha_after.txt"
echo "CH01_17_SOURCE_UNCHANGED_PASS"

stage COLCON_BUILD_ISOLATED_REAL_TEXTBOOK_PACKAGE
cd "$TMP/ws"
timeout --signal=TERM --kill-after=5s 90s \
  colcon build --symlink-install --packages-select my_robot_controller \
  > "$OUT/colcon.log" 2>&1
set +u; source "$TMP/ws/install/setup.bash"; set -u
PREFIX="$(ros2 pkg prefix my_robot_controller)"
printf '%s\n' "$PREFIX" > "$OUT/prefix.txt"
test "$PREFIX" = "$TMP/ws/install/my_robot_controller"
BASE="$PREFIX/share/my_robot_controller"
test -f "$BASE/package.xml"
test -f "$BASE/launch/asset_demo.launch.py"
test -f "$BASE/config/lesson.yaml"
cmp "$PKG/launch/asset_demo.launch.py" "$BASE/launch/asset_demo.launch.py"
cmp "$PKG/config/lesson.yaml" "$BASE/config/lesson.yaml"
ros2 pkg executables my_robot_controller > "$OUT/executables.txt"
grep -q 'my_robot_controller test_node' "$OUT/executables.txt"
python3 - "$BASE/package.xml" "$BASE/config/lesson.yaml" "$OUT/manifest_audit.json" <<'PY'
import json
from pathlib import Path
import sys, xml.etree.ElementTree as ET
import yaml
root=ET.parse(sys.argv[1]).getroot()
assert root.findtext("name")=="my_robot_controller"
dependencies={e.text for e in root.findall("depend")}
assert {"rclpy","std_msgs"}.issubset(dependencies)
data=yaml.safe_load(Path(sys.argv[2]).read_text())
assert data["purpose"]=="ament_python data_files installation"
assert data["hardware_command"] is False
out={"package":"my_robot_controller","dependencies":sorted(dependencies),
     "installed_manifest":True,"installed_launch":True,"installed_config":True,
     "launch_config_file_matches_source":True,"original_textbook_source_unchanged":True,
     "rosdep_install":"NOT_RUN_EXISTING_ROS_BASE","hardware":"NOT_RUN"}
Path(sys.argv[3]).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print("CH01_17_INSTALLED_MANIFEST_ASSETS_AND_ENTRYPOINT_PASS",flush=True)
PY

stage EXECUTE_INSTALLED_LAUNCH_VIA_REAL_ROS_CLI
timeout --signal=TERM --kill-after=4s 25s \
  ros2 launch my_robot_controller asset_demo.launch.py \
  > "$OUT/installed_launch.log" 2>&1
cat "$OUT/installed_launch.log"
grep -q CH01_17_ACTUAL_INSTALLED_LAUNCH_DISCOVERED "$OUT/installed_launch.log"
stage FINAL_AUDIT
sha256sum "$ORIGINAL/setup.py" > "$OUT/original_setup_sha_after.txt"
cmp "$OUT/original_setup_sha_before.txt" "$OUT/original_setup_sha_after.txt"
python3 - "$OUT/manifest_audit.json" "$OUT/result.json" <<'PY'
import json,os,sys
from pathlib import Path
x=json.loads(Path(sys.argv[1]).read_text())
x.update({"chapter":"Ch01","section":"1.7","status":"SCOPED_PASS",
          "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
          "scope":"real_colcon_isolated_copy_data_files_launch_config_and_ros2_launch",
          "original_1hz_node_retest":"NOT_RUN","ch10":"HOLD"})
Path(sys.argv[2]).write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
PY
echo CH01_17_REAL_COLCON_DATA_FILES_AND_ROS2_LAUNCH_SCOPED_PASS
