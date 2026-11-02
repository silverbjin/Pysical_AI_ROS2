python3 - "$BLOCKED_OUT" "$CANCEL_OUT" "$LOSS_OUT" <<'PY_FAILURES'
from pathlib import Path
import json, sys
for folder, expected in zip(sys.argv[1:], [6, 5, 5]):
    p = Path(folder); s = json.loads((p/'navigation_summary.json').read_text())
    v = json.loads((p/'navigation_verification.json').read_text())
    print(s['case'], s['result'], 'terminal=', s['terminal_status'],
          'motion=', v['motion_witness_m'], 'settle=', s['terminal_to_settled_wall_s'])
    assert s['result'] == v['result'] == 'PASS' and s['terminal_status'] == expected
loss = json.loads((Path(sys.argv[3])/'navigation_summary.json').read_text())
print('raw receipt -> zero decision s:', loss['raw_expiry_decision_latency_s'])
assert loss['raw_expiry_decision_latency_s'] <= .35
assert loss['no_auto_resume_after_raw_return']
PY_FAILURES
