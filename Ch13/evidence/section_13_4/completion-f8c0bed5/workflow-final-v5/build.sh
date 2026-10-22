source .superpowers/sdd/2026-10-21-completion/env.sh
label="$1"
test ! -e "$CH13_EGL_EVIDENCE/$label.log" || exit 90
python -m colcon --log-base "$CH13_EGL_LOG" build --base-paths Ch13/ros2_ws/src --build-base "$CH13_EGL_BUILD" --install-base "$CH13_EGL_INSTALL" --packages-select integrated_robot_interfaces integrated_robot_vision integrated_robot_description integrated_robot_runtime integrated_robot_camera integrated_robot_controller --cmake-args -DPython3_EXECUTABLE=/home/jinho/ch13_vision_13_4_venv/bin/python > "$CH13_EGL_EVIDENCE/$label.log" 2>&1
status=$?
tail -n 12 "$CH13_EGL_EVIDENCE/$label.log"
exit "$status"
