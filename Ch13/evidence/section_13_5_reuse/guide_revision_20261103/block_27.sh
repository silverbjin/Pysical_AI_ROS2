git switch -c lab/ch13-13-5-free-080
python3 - <<'PY_EDIT'
from pathlib import Path
p = Path('Ch13/scripts/reuse_13_5/run_navigation_probe.py')
s = p.read_text()
old = 'target=[.65,0.,0.]'
assert s.count(old) == 1
p.write_text(s.replace(old, 'target=[.80,0.,0.]'))
PY_EDIT
export CUSTOM_OUT="$LAB_EVIDENCE/free_080"
bash Ch13/scripts/reuse_13_5/run_navigation.sh free "$CUSTOM_OUT"
