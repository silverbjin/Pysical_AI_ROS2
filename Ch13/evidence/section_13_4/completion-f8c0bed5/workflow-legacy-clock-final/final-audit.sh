set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
python "$CH13_EGL_EVIDENCE/collect_final.py" "$CH13_EGL_EVIDENCE/final-v5" "$CH13_EGL_EVIDENCE/legacy-clock-final"
python .superpowers/sdd/2026-10-21-completion/final-audit.py
