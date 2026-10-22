set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
require_pass() {
    python -c 'import json,sys; from pathlib import Path; r=json.loads(Path(sys.argv[1]).read_text()); assert r["status"]=="PASS",r["status"]' "$CH13_EGL_EVIDENCE/$1/result.json"
}
require_pass reaped-images-a
for suffix in b c; do
    bash .superpowers/sdd/2026-10-21-completion/trial.sh "reaped-images-$suffix" mujoco safety --fault images --trace-enabled
    require_pass "reaped-images-$suffix"
done
bash .superpowers/sdd/2026-10-21-completion/trial.sh reaped-gazebo-images gazebo safety --fault images --trace-enabled
require_pass reaped-gazebo-images
bash .superpowers/sdd/2026-10-21-completion/test.sh source-final-v5 Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test
bash .superpowers/sdd/2026-10-21-completion/package-regression.sh package-final-v5
export CH13_FINAL_NAME=final-v5
bash .superpowers/sdd/2026-10-21-completion/final-matrix.sh freeze
for mode in geometry tracking remaining legacy; do
    bash .superpowers/sdd/2026-10-21-completion/final-matrix.sh "$mode"
done
