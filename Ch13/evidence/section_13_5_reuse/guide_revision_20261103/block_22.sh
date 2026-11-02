python3 - "$VISION_OUT" <<'PY_MODE'
from pathlib import Path
import json, sys
s = json.loads((Path(sys.argv[1])/'navigation_summary.json').read_text())
print('motion admission:', s['motion_admission'])
print('terminal:', s['terminal_status'])
print('handoff:', s['ready_for_manipulation']['state'])
a = s['motion_admission']
assert a['held'] and a['boundary_phase'] == 'ACTIVE'
assert a['gateway_arm_wall'] <= a['platform_arm_wall'] <= a['release_wall']
PY_MODE
