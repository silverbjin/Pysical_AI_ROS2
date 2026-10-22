source .superpowers/sdd/2026-10-21-completion/env.sh
label="${1:-render-probe}"
camera="${2:-overview}"
test ! -e "$CH13_EGL_EVIDENCE/$label.log" || exit 90
python "$CH13_EGL_EVIDENCE/render_probe.py" "$camera" > "$CH13_EGL_EVIDENCE/$label.log" 2>&1
status=$?
tail -n 60 "$CH13_EGL_EVIDENCE/$label.log"
exit "$status"
