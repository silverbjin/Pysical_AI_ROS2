set -e -o pipefail
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
test ! -e "$CH13_EGL_EVIDENCE/numeric-budget-compiled.json" || exit 90
OPENCV_FOR_THREADS_NUM=1 python Ch13/evidence/section_13_4/completion-f8c0bed5/numeric_budget_probe.py compiled 2>&1 | tee "$CH13_EGL_EVIDENCE/numeric-budget-compiled.json"
