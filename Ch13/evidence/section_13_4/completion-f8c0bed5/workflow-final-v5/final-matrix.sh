set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
python .superpowers/sdd/2026-10-21-completion/final-matrix.py "$@"
