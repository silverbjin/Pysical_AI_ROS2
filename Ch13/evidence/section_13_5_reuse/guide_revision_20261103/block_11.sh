python3 - "$FREE_OUT" <<'PY_FREE'
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
s = json.loads((p/'navigation_summary.json').read_text())
v = json.loads((p/'navigation_verification.json').read_text())
r = json.loads((p/'residual_processes.json').read_text())
print('run/verify/cleanup:', s['result'], v['result'], r['result'])
print('terminal:', s['terminal_status'], 'target:', s['target'])
print('actual position/yaw error:', s['actual_goal_error_m'], s['actual_goal_yaw_error_rad'])
assert (s['result'], v['result'], r['result']) == ('PASS', 'PASS', 'PASS')
assert s['terminal_status'] == 4
PY_FREE
