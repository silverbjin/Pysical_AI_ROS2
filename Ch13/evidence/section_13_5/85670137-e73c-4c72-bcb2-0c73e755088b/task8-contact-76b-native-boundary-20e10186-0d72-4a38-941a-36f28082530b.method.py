"""Post-reap actual physics command snapshots, no controller/engine execution."""
import json,hashlib,uuid,collections,statistics
from pathlib import Path
base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
name='native-contact-component-gazebo-76b1aac2-c54c-4178-8ac1-6b77616792de'
trial=base/name;c=json.loads((trial/'controller_report.json').read_text());fault=c['first_fault']
teardown=json.loads((trial/'teardown.json').read_text());assert teardown['parent_reaped'] and not teardown['residual_live_pids']
path=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/name/'native_controls.json'
raw=path.read_bytes();data=json.loads(raw)
print('CONTROL ROOT',type(data).__name__,list(data)[:8] if isinstance(data,dict) else len(data))
if isinstance(data,dict):data=data.get('records',data.get('samples',data.get('frames',data.get('controls',[]))))
assert isinstance(data,list) and data
print('FIRST KEYS',list(data[0]))
start=fault['phase_context']['_unload_start'];end=fault['ros_ns']
rows=[p for p in data if start<=p['capture_ns']<=end]
assert rows
keys=('name','position','velocity','force_command','position_reference','projected_transmitted_effort','applied_generalized_force')
selected=[dict(capture_ns=p['capture_ns'],joints=[{k:j.get(k) for k in keys} for j in p['joints'] if j['name'] in ('fr_calf_joint','fl_calf_joint','rr_calf_joint','rl_calf_joint')]) for p in rows]
stamps=[next(j for j in p['joints'] if j['name']=='fl_calf_joint')['position_reference']['write_capture_ns'] for p in rows]
unique=list(dict.fromkeys(stamps));deltas=collections.Counter(b-a for a,b in zip(unique,unique[1:]))
result=dict(scope='post_reap_native_boundary_not_applied_generalized_force',input=str(path),input_sha256=hashlib.sha256(raw).hexdigest(),
 total_packets=len(data),unload_packets=len(rows),unique_write_captures=len(unique),write_delta_ns=dict(deltas),
 first_rows=selected[:12],last_rows=selected[-12:],last_full_packet=rows[-1])
out=base/f'task8-contact-76b-native-boundary-{uuid.uuid4()}.json';out.write_text(json.dumps(result,indent=2)+'\n')
out.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(output=str(out),total_packets=len(data),unload_packets=len(rows),unique_write_captures=len(unique),write_deltas=dict(deltas),last_joints=selected[-1]),indent=2))
