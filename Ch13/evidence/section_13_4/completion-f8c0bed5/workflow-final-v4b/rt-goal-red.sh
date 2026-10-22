set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
label="${1:?new label required}"
test ! -e "$CH13_EGL_EVIDENCE/$label-build.log" || exit 90
cmake -S "$CH13_EGL_EVIDENCE/rt-goal-repro" -B .superpowers/sdd/2026-10-21-completion/rt-goal-build > "$CH13_EGL_EVIDENCE/$label-configure.log" 2>&1
cmake --build .superpowers/sdd/2026-10-21-completion/rt-goal-build -j2 > "$CH13_EGL_EVIDENCE/$label-build.log" 2>&1
set +e
.superpowers/sdd/2026-10-21-completion/rt-goal-build/rt_goal_original > "$CH13_EGL_EVIDENCE/$label-red.log" 2>&1
status=$?
cat "$CH13_EGL_EVIDENCE/$label-red.log"
exit "$status"
