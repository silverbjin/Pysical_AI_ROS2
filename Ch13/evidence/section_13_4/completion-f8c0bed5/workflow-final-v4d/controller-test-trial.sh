set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
test ! -e "$CH13_EGL_EVIDENCE/controller-unit.log" || exit 90
python -m colcon --log-base "$CH13_EGL_LOG" test --base-paths Ch13/ros2_ws/src --build-base "$CH13_EGL_BUILD" --install-base "$CH13_EGL_INSTALL" --packages-select integrated_robot_controller --executor sequential > "$CH13_EGL_EVIDENCE/controller-unit.log" 2>&1
python -m colcon test-result --test-result-base "$CH13_EGL_BUILD/integrated_robot_controller" > "$CH13_EGL_EVIDENCE/controller-unit-result.log" 2>&1
cat "$CH13_EGL_EVIDENCE/controller-unit-result.log"
bash .superpowers/sdd/2026-10-21-completion/action-trial.sh controller-rpc-m10 mujoco tracking --trace-enabled
