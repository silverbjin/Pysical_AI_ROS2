from pathlib import Path
import json, sys
p = Path(sys.argv[1]); s = json.loads((p/'navigation_summary.json').read_text())
v = json.loads((p/'navigation_verification.json').read_text())
a = s['vision_admission']; ready = s['ready_for_manipulation']
print('result:', s['result'], v['result'], 'terminal:', s['terminal_status'])
print('observed surface:', a['source_observation']['point'])
print('evaluated candidate count:', len(a['candidate_evaluations']))
print('selected pose:', a['selected']['pose'])
print('actual errors:', s['actual_goal_error_m'], s['actual_goal_yaw_error_rad'])
print('settling wall s:', s['terminal_to_settled_wall_s'])
print('READY:', ready['state'], 'photo age:', ready['decision_wall']-ready['capture_wall'])
print('final workspace:', s['final_arm_workspace'])
assert s['result'] == v['result'] == 'PASS' and s['terminal_status'] == 4
assert s['goal_header_stamp_ns'] == a['source_observation']['capture_ns']
assert ready['state'] == 'READY_FOR_MANIPULATION'
