set -e -o pipefail
source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
test ! -e "$CH13_EGL_EVIDENCE/numeric-budget-default.json" || exit 90
python Ch13/evidence/section_13_4/completion-f8c0bed5/numeric_budget_probe.py default 2>&1 | tee "$CH13_EGL_EVIDENCE/numeric-budget-default.json"
OPENCV_FOR_THREADS_NUM=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python Ch13/evidence/section_13_4/completion-f8c0bed5/numeric_budget_probe.py one_thread 2>&1 | tee "$CH13_EGL_EVIDENCE/numeric-budget-one.json"
