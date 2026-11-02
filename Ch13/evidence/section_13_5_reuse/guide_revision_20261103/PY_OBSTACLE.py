from pathlib import Path
import json, sys
p = Path(sys.argv[1]); s = json.loads((p/'navigation_summary.json').read_text())
print('result=', s['result'], 'terminal=', s['terminal_status'])
print('target=', s['target'], 'max |actual y|=', s['max_abs_y_m'])
assert s['result'] == 'PASS' and s['terminal_status'] == 4
assert s['max_abs_y_m'] > .45
