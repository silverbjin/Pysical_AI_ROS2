set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
bash .superpowers/sdd/2026-10-21-completion/test.sh source-final-v5-probe Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test
python .superpowers/sdd/2026-10-21-completion/legacy-clock-final.py
