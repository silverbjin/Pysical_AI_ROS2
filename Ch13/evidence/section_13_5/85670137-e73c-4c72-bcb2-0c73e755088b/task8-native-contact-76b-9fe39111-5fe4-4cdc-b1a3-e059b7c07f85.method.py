"""One post-reap pass over selected C1 observations, no engine/ROS imports."""
import json,hashlib,uuid,math
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
trial=base/'native-contact-component-gazebo-76b1aac2-c54c-4178-8ac1-6b77616792de'
c=json.loads((trial/'controller_report.json').read_text());f=c['first_fault'];obs=f['load_transfer_observation']
summary={
 'reason':f['reason'],'state_before':f['state_before'],'phase_context':f['phase_context'],
 'targets':f['targets'],'reference_body':f['reference_body'],'stance_reference_z':f['stance_reference_z'],
 'force_sample':f['samples']['contacts'],
 'linear_model':obs['linear_model'],'attempt':obs['attempt'],
 'application_scaling':obs.get('application_scaling'),
 'args':obs['numeric_input'],'worker':c['numeric_worker'],
}
data=json.loads((trial/'all_frames.json').read_text())
summary['frames_type']=type(data).__name__
if isinstance(data,dict):summary['frame_keys']=list(data)
else:summary['first_frame_keys']=list(data[0]) if data else []
out=base/f'task8-native-contact-76b-{uuid.uuid4()}.json'
summary['input_hashes']={n:hashlib.sha256((trial/n).read_bytes()).hexdigest() for n in ('controller_report.json','all_frames.json','source_manifest.json','install_manifest.json')}
out.write_text(json.dumps(summary,indent=2)+'\n');out.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(out)
print(json.dumps({k:v for k,v in summary.items() if k not in ('args','reference_body','linear_model','force_sample')},indent=2)[:9000])
print('FRAMES PEEK',str(data)[:2200])
