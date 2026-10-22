set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
python -c 'import json; from pathlib import Path; r=json.loads(Path("Ch13/evidence/section_13_4/completion-f8c0bed5/controller-rpc-m10/result.json").read_text()); assert r["status"]=="PASS",r["status"]'
bash .superpowers/sdd/2026-10-21-completion/test.sh source-final-v4 Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test
bash .superpowers/sdd/2026-10-21-completion/package-regression.sh package-final-v4
export CH13_FINAL_NAME=final-v4
bash .superpowers/sdd/2026-10-21-completion/final-matrix.sh freeze
for mode in geometry tracking remaining legacy; do
    bash .superpowers/sdd/2026-10-21-completion/final-matrix.sh "$mode"
done
