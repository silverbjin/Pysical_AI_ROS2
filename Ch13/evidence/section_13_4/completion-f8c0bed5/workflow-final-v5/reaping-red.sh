source .superpowers/sdd/2026-10-21-completion/env.sh
source "$CH13_EGL_INSTALL/setup.bash"
python "$CH13_EGL_EVIDENCE/child_reaping_race.py" > "$CH13_EGL_EVIDENCE/child-reaping-race.log" 2>&1
cat "$CH13_EGL_EVIDENCE/child-reaping-race.log"
bash .superpowers/sdd/2026-10-21-completion/test.sh runtime-reaping-red Ch13/tests/test_runtime_shutdown_order.py -k parent_reaping
