set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
test ! -e "$CH13_EGL_EVIDENCE/rt-goal-patched.log" || exit 90
cmake -S "$CH13_EGL_EVIDENCE/rt-goal-repro" -B .superpowers/sdd/2026-10-21-completion/rt-goal-build -DCH13_PATCH_INCLUDE="$PWD/Ch13/ros2_ws/src/integrated_robot_controller/include" > "$CH13_EGL_EVIDENCE/rt-goal-patched-configure.log" 2>&1
cmake --build .superpowers/sdd/2026-10-21-completion/rt-goal-build -j2 > "$CH13_EGL_EVIDENCE/rt-goal-patched-build.log" 2>&1
set +e
.superpowers/sdd/2026-10-21-completion/rt-goal-build/rt_goal_original > "$CH13_EGL_EVIDENCE/rt-goal-original-confirm.log" 2>&1
original=$?
.superpowers/sdd/2026-10-21-completion/rt-goal-build/rt_goal_patched > "$CH13_EGL_EVIDENCE/rt-goal-patched.log" 2>&1
patched=$?
cat "$CH13_EGL_EVIDENCE/rt-goal-original-confirm.log" "$CH13_EGL_EVIDENCE/rt-goal-patched.log"
test "$original" -eq 1 && test "$patched" -eq 0
