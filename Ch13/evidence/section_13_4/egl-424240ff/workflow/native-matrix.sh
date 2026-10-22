set -e
source .superpowers/sdd/2026-10-20-egl-camera-latency-plan/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
python .superpowers/sdd/2026-10-20-egl-camera-latency-plan/native-matrix.py "$@"
