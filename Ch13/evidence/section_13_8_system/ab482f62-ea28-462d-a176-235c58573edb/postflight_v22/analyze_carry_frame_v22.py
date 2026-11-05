"""Offline frame comparison; does not replace the original physical verdict."""
import json,math,sys
from pathlib import Path
case=Path(sys.argv[1]);output=case/'carry_frame_analysis_v22.json'
assert not output.exists()
engine=json.loads((case/'engine.json').read_text())
rows=[r for r in engine['pick_physics']['rows'] if r['phase']=='CARRY']
a=rows[0];lowest=min(rows,key=lambda r:r['target'][2])
report=dict(scope='diagnosis only; original carry_height FAIL remains unchanged',
 samples=len(rows),first=a,lowest_world_z=lowest,
 world_target_drop_m=a['target'][2]-lowest['target'][2],
 world_tcp_drop_at_lowest_m=a['tcp'][2]-lowest['tcp'][2],
 relative_slip_at_lowest_m=math.dist(a['relative_tcp'],lowest['relative_tcp']),
 max_relative_slip_m=max(math.dist(a['relative_tcp'],r['relative_tcp']) for r in rows),
 max_support_force_during_carry_N=max(r['target_support_N'] for r in rows))
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('first','lowest_world_z')},indent=2))