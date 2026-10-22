source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
# Test conftest files select current source. Leave child-process PYTHONPATH
# installed-only so the independent installation audit can reject stale code.
label="$1"
shift
test ! -e "$CH13_EGL_EVIDENCE/$label.log" || exit 90
python -m pytest "$@" -q --junitxml="$CH13_EGL_EVIDENCE/$label.xml" > "$CH13_EGL_EVIDENCE/$label.log" 2>&1
status=$?
tail -n 30 "$CH13_EGL_EVIDENCE/$label.log"
exit "$status"
