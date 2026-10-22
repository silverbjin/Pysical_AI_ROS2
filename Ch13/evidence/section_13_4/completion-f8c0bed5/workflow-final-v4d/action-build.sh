set -e
source .superpowers/sdd/2026-10-21-completion/env.sh
includes=()
for include in /opt/ros/jazzy/include/*; do includes+=("-I$include"); done
cc -shared -fPIC -Wall -Wextra "${includes[@]}" "$CH13_EGL_EVIDENCE/action_boundary.c" -ldl -o .superpowers/sdd/2026-10-21-completion/action_boundary.so
sha256sum "$CH13_EGL_EVIDENCE/action_boundary.c" .superpowers/sdd/2026-10-21-completion/action_boundary.so
