set -e
source .superpowers/sdd/2026-10-20-egl-camera-latency-plan/env.sh
python .superpowers/sdd/2026-10-20-egl-camera-latency-plan/analyze-native.py > "$CH13_EGL_EVIDENCE/native-analysis.log"
tail -n 20 "$CH13_EGL_EVIDENCE/native-analysis.log"
