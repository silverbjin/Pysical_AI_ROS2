set -e
source .superpowers/sdd/2026-10-20-egl-camera-latency-plan/env.sh
python .superpowers/sdd/2026-10-20-egl-camera-latency-plan/gate-neighbors.py > "$CH13_EGL_EVIDENCE/gate-neighbors.log"
tail -n 40 "$CH13_EGL_EVIDENCE/gate-neighbors.log"
