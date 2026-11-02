import json,hashlib,uuid,statistics,math
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
trial=base/'native-contact-component-gazebo-76b1aac2-c54c-4178-8ac1-6b77616792de'
c=json.loads((trial/'controller_report.json').read_text());fault=c['first_fault']
start=fault['phase_context']['_unload_start'];end=fault['ros_ns'];selected=fault['state_before']['swing_foot']
all_frames=json.loads((trial/'all_frames.json').read_text())['frames']
seen=set();rows=[]
for frame in all_frames:
    sample=frame.get('samples',{}).get('contacts')
    if not sample or not start<=sample['stamp_ns']<=end or sample['stamp_ns'] in seen:continue
    seen.add(sample['stamp_ns']);d=sample['data'];i=d['names'].index(selected)
    rows.append(dict(t=(sample['stamp_ns']-start)/1e9,force=d['forces'][i],vectors=d.get('forces_world'),
        body=frame['samples'].get('body',{}).get('data'),joints=frame['samples']['joints']['data']))
bins=[]
for t in (0.,1.,2.,3.,4.,5.,6.):
    if rows:
        r=min(rows,key=lambda row:abs(row['t']-t));bins.append({k:r[k] for k in ('t','force','vectors')})
out=base/f'task8-contact-76b-series-{uuid.uuid4()}.json'
result=dict(scope='post_reap_selected_capture_summary_no_new_engine_or_acceptance',selected=selected,
 start_ros_ns=start,end_ros_ns=end,unique_captures=len(rows),force_bins=bins,
 min_selected_force_n=min(r['force'] for r in rows),last_selected_force_n=rows[-1]['force'],
 sample_names=list(all_frames[-1]['samples']),publication_last=c['command_publications']['rows'][-1],
 input_sha256=hashlib.sha256((trial/'all_frames.json').read_bytes()).hexdigest())
out.write_text(json.dumps(result,indent=2)+'\n');out.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(out);print(json.dumps(result,indent=2))
