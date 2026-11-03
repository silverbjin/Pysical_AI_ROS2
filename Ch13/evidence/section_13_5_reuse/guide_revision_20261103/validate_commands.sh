#!/usr/bin/env bash
set -e
reuse_clone=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_guide_validation_20261103
reuse_validation=/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse/Ch13/evidence/section_13_5_reuse/guide_revision_20261103
export CH13_REUSE_VENV=/home/jinho/ch13_reuse_iit_d010212_venv CH13_REUSE_BUILD=/home/jinho/ch13_reuse_r5_build
export ROS_DOMAIN_ID=135 ROS_LOCALHOST_ONLY=1 PYTHONDONTWRITEBYTECODE=1
cd "$reuse_clone"
source /opt/ros/jazzy/setup.bash
source "$CH13_REUSE_BUILD/install/setup.bash"
for reuse_block in "$reuse_validation"/block_*.sh; do bash -n "$reuse_block"; done
printf 'BASH_SYNTAX_PASS_28\n'
python3 "$reuse_validation/PY_SOURCE.py"
python3 "$reuse_validation/PY_ASSETS.py"
"$CH13_REUSE_VENV/bin/python" "$reuse_validation/PY_VERSIONS.py"
for reuse_name in PY_PARAMS PY_SLEW PY_IK; do bash Ch13/scripts/reuse_13_5/env_r2.sh "$reuse_validation/$reuse_name.py"; done
bash Ch13/scripts/reuse_13_5/env_r2.sh Ch13/scripts/reuse_13_5/audit_r2_install.py "$reuse_validation/cloned_install_audit.json"
ros2 topic echo --help >/dev/null
ros2 action list --help >/dev/null
printf 'GUIDE_PREFLIGHT_PASS\n'
