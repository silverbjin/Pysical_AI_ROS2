source .superpowers/sdd/2026-10-20-egl-camera-latency-plan/env.sh
label="${1:-build}"
python -m colcon --log-base "$CH13_EGL_LOG" build --base-paths Ch13/ros2_ws/src --build-base "$CH13_EGL_BUILD" --install-base "$CH13_EGL_INSTALL" --packages-select integrated_robot_interfaces integrated_robot_vision integrated_robot_description integrated_robot_runtime integrated_robot_camera --cmake-args -DPython3_EXECUTABLE=/home/jinho/ch13_vision_13_4_venv/bin/python > "$CH13_EGL_EVIDENCE/$label.log" 2>&1
status=$?
tail -n 10 "$CH13_EGL_EVIDENCE/$label.log"
exit "$status"
