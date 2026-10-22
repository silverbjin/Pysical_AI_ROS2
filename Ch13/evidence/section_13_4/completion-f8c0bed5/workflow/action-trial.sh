set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
bash .superpowers/sdd/2026-10-21-completion/action-build.sh > "$CH13_EGL_EVIDENCE/$1-action-library.log" 2>&1
export LD_PRELOAD="$PWD/.superpowers/sdd/2026-10-21-completion/action_boundary.so"
bash .superpowers/sdd/2026-10-21-completion/trial.sh "$@"
