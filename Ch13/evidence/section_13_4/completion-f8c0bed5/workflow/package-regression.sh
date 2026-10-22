set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
label="${1:?label required}"
test ! -e "$CH13_EGL_EVIDENCE/$label-colcon.log" || exit 90
python -m colcon --log-base "$CH13_EGL_LOG" test --base-paths Ch13/ros2_ws/src --build-base "$CH13_EGL_BUILD" --install-base "$CH13_EGL_INSTALL" --executor sequential > "$CH13_EGL_EVIDENCE/$label-colcon.log" 2>&1
tail -n 12 "$CH13_EGL_EVIDENCE/$label-colcon.log"
python -m colcon test-result --test-result-base "$CH13_EGL_BUILD" > "$CH13_EGL_EVIDENCE/$label-result.log" 2>&1
tail -n 8 "$CH13_EGL_EVIDENCE/$label-result.log"
python Ch13/scripts/verify_all_13_4.py --audit-install-prefix "$CH13_EGL_INSTALL" > "$CH13_EGL_EVIDENCE/$label-installed.json" 2> "$CH13_EGL_EVIDENCE/$label-installed.stderr"
