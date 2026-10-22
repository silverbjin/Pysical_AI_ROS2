set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
export ROS_DOMAIN_ID=158
test ! -e "$CH13_EGL_EVIDENCE/clock-load.log" || exit 90
python "$CH13_EGL_EVIDENCE/clock_load_probe.py" > "$CH13_EGL_EVIDENCE/clock-load.log" 2>&1
tail -n 40 "$CH13_EGL_EVIDENCE/clock-load.log"
