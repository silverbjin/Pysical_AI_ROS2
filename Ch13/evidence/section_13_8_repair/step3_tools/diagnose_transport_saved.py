"""Post-exit exact first safety sample and original height decomposition."""
import json,math,sys
import numpy as np
from scipy.spatial.transform import Rotation
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists();base=root/'Ch13/evidence/section_13_8_system'
case=base/'dee84795-4b0b-49ac-9a92-c0d9f8af69ad';e=json.loads((case/'engine.json').read_text());events=e['manipulation']['events'];fault=next(r for r in events if r.get('fault')=='TRANSPORT_PLATFORM_UNSAFE');samples=[json.loads(l) for l in (case/'last_stop_500hz.jsonl').open()]
def metrics(row):
 q=row['qpos'];v=row['qvel'];return dict(sim_s=row['sim_s'],wall=row['wall'],base_xyz=q[:3],mode=row['mode'],command_vx=row['vx'],command_wz=row['wz'],tilt_rad=math.acos(max(-1,min(1,1-2*(q[4]**2+q[5]**2)))),vxy=math.hypot(v[0],v[1]),wz=abs(v[5]))
ns=fault['stamp_ns'];near=[metrics(r) for r in samples if abs(r['sim_s']-ns/1e9)<.012];exact=min(samples,key=lambda r:abs(r['sim_s']-ns/1e9));safety=dict(first_fault=fault,exact_sample=metrics(exact),near=near,time_residual_s=abs(exact['sim_s']-ns/1e9))
case=base/'621d134d-be0a-405c-af20-e5ac913940b7';e=json.loads((case/'engine.json').read_text());rows=e['pick_physics']['rows'];carry=[r for r in rows if r['phase']=='CARRY'];first=carry[0];low=min(carry,key=lambda r:r['target'][2]);
def delta(a,b):return [x-y for x,y in zip(a,b)]
height=dict(baseline=first,lowest=low,target_drop_m=first['target'][2]-low['target'][2],tcp_drop_m=first['tcp'][2]-low['tcp'][2],base_drop_m=first['base_xyz'][2]-low['base_xyz'][2],relative_world_drop_m=(first['target'][2]-first['tcp'][2])-(low['target'][2]-low['tcp'][2]),max_relative_tcp_change_m=max(math.dist(r['relative_tcp'],first['relative_tcp']) for r in carry),dual_contact_fraction=sum(all(r['target_contact_N'].get(f,0)>.005 for f in ('link7','link8')) for r in carry)/len(carry),min_target_support_N=min(r['target_support_N'] for r in carry),phase_counts={p:sum(r['phase']==p for r in carry) for p in sorted({r['phase'] for r in carry})},minimum_clearance_m=min(r['target'][2]-.04 for r in carry))
engine_rows=[json.loads(line) for line in (case/'engine_observations.jsonl').open()]
a=min(engine_rows,key=lambda r:abs(r['sim_s']-first['sim_s']));b=min(engine_rows,key=lambda r:abs(r['sim_s']-low['sim_s']))
R0=Rotation.from_quat(np.roll(a['qpos'][3:7],-1)).as_matrix();R1=Rotation.from_quat(np.roll(b['qpos'][3:7],-1)).as_matrix()
v0=R0.T@(np.array(first['tcp'])-first['base_xyz']);v1=R1.T@(np.array(low['tcp'])-low['base_xyz'])
height['tcp_world_delta_components_m']=dict(base_translation_z=low['base_xyz'][2]-first['base_xyz'][2],base_orientation_z=float(((R1-R0)@v0)[2]),arm_relative_z=float((R1@(v1-v0))[2]),orientation_sample_offsets_s=[a['sim_s']-first['sim_s'],b['sim_s']-low['sim_s']],scope='body orientations from nearest20ms engine samples; base/TCP exact physical rows')
result=dict(scope='original v28 failures; safety thresholds and physical verdict unchanged',safety=safety,height=height)
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(safety=safety,height={k:v for k,v in height.items() if k not in ('baseline','lowest')}),indent=2))
