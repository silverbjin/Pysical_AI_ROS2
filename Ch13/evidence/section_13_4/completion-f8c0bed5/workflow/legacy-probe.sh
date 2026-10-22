set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
export CH13_EGL_EVIDENCE="$CH13_EGL_EVIDENCE/legacy-probe"
test ! -e "$CH13_EGL_EVIDENCE" || exit 90
mkdir "$CH13_EGL_EVIDENCE"
python Ch13/evidence/section_13_4/egl-424240ff/workflow/legacy.py
