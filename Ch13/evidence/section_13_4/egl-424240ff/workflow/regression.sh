source .superpowers/sdd/2026-10-20-egl-camera-latency-plan/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
label="${1:?label required}"
python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_vision/test Ch13/ros2_ws/src/integrated_robot_runtime/test -q --junitxml="$CH13_EGL_EVIDENCE/$label-pytest.xml" > "$CH13_EGL_EVIDENCE/$label-pytest.log" 2>&1
status=$?
tail -n 5 "$CH13_EGL_EVIDENCE/$label-pytest.log"
if [ "$status" -ne 0 ]; then exit "$status"; fi
python -m colcon --log-base "$CH13_EGL_LOG" test --base-paths Ch13/ros2_ws/src --build-base "$CH13_EGL_BUILD" --install-base "$CH13_EGL_INSTALL" --executor sequential > "$CH13_EGL_EVIDENCE/$label-colcon.log" 2>&1
status=$?
tail -n 7 "$CH13_EGL_EVIDENCE/$label-colcon.log"
if [ "$status" -ne 0 ]; then exit "$status"; fi
python -m colcon test-result --test-result-base "$CH13_EGL_BUILD" > "$CH13_EGL_EVIDENCE/$label-result.log" 2>&1
status=$?
tail -n 5 "$CH13_EGL_EVIDENCE/$label-result.log"
if [ "$status" -ne 0 ]; then exit "$status"; fi
python Ch13/scripts/verify_all_13_4.py --audit-install-prefix "$CH13_EGL_INSTALL" > "$CH13_EGL_EVIDENCE/$label-installed.json" 2> "$CH13_EGL_EVIDENCE/$label-installed.stderr"
exit "$?"
