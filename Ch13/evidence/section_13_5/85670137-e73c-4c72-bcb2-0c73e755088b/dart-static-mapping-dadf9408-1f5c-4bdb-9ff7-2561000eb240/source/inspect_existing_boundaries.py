"""Read only existing 2ms event snapshots; missing samples do not imply missing calls."""
import collections, json
from pathlib import Path
root=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
p=root/'native-contact-component-gazebo-d50469aa-b0a0-402b-b8e5-f59f21ad31a0/native_controls.json'
d=json.loads(p.read_bytes())
records=d['records']
print('records',len(records),'first_keys',list(records[0]))
events=[]
for r in records:
 for b in r.get('body_references',[]):
  j=b.get('contact_event_joints')
  if j:
   row=next(v for v in j['joints'] if v['name']=='fl_calf_joint')
   events.append({'capture_ns':j['capture_ns'],'state_capture_ns':j.get('state_capture_ns'),
      'write_capture_ns':row.get('position_reference',{}).get('write_capture_ns'),
      'command':row['force_command'],'wrench':row['projected_transmitted_effort'], 'qd':row['velocity']})
print('event_samples',len(events))
print('write_age_ns',collections.Counter(e['capture_ns']-e['write_capture_ns'] for e in events if e['write_capture_ns'] is not None))
print('event_gap_ns',collections.Counter(b['capture_ns']-a['capture_ns'] for a,b in zip(events,events[1:])).most_common(8))
print('examples',json.dumps(events[:12],indent=2))
print('last',json.dumps(events[-4:],indent=2))
