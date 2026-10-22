set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
export CH13_EGL_EVIDENCE="$CH13_EGL_EVIDENCE/${1:?label}"
test ! -e "$CH13_EGL_EVIDENCE" || exit 90
mkdir "$CH13_EGL_EVIDENCE"
python .superpowers/sdd/2026-10-21-completion/legacy-target.py "${2:?engine}"
