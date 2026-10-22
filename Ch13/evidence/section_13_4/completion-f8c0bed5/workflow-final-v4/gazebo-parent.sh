set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
test ! -e "$CH13_EGL_EVIDENCE/gazebo-parent-completion" || exit 90
python "$CH13_EGL_EVIDENCE/gazebo_parent_probe.py" > "$CH13_EGL_EVIDENCE/gazebo-parent-runner.log" 2>&1
