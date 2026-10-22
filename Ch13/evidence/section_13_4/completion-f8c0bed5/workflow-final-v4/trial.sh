set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
label="$1"
shift
test ! -e "$CH13_EGL_EVIDENCE/$label" || exit 90
python .superpowers/sdd/2026-10-21-completion/trial.py "$label" "$@"
