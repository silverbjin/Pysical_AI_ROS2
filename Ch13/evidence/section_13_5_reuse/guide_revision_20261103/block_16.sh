export OBSTACLE_OUT="$LAB_EVIDENCE/obstacle"
printf '%s\n' "$OBSTACLE_OUT" > "$REUSE_WORK/current_run.txt"
bash Ch13/scripts/reuse_13_5/run_navigation.sh obstacle "$OBSTACLE_OUT"
python3 - "$OBSTACLE_OUT" <<'PY_OBSTACLE'
from pathlib import Path
import json, sys
p = Path(sys.argv[1]); s = json.loads((p/'navigation_summary.json').read_text())
print('result=', s['result'], 'terminal=', s['terminal_status'])
print('target=', s['target'], 'max |actual y|=', s['max_abs_y_m'])
assert s['result'] == 'PASS' and s['terminal_status'] == 4
assert s['max_abs_y_m'] > .45
PY_OBSTACLE
