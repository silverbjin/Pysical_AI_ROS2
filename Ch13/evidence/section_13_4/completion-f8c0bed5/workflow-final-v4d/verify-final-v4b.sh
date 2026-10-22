set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
bash .superpowers/sdd/2026-10-21-completion/test.sh source-final-v4b Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test
bash .superpowers/sdd/2026-10-21-completion/package-regression.sh package-final-v4b
export CH13_FINAL_NAME=final-v4
bash .superpowers/sdd/2026-10-21-completion/final-matrix.sh freeze
for mode in geometry tracking remaining legacy; do
    bash .superpowers/sdd/2026-10-21-completion/final-matrix.sh "$mode"
done
