"""Bounded summary of one completed G1's final candidate window, no acceptance override."""
import bisect,hashlib,json,math,uuid
from collections import Counter
from pathlib import Path
repo=Path.cwd();task=Path(__file__).resolve()
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/'native-g1-gazebo-1e7eda2b-2dd4-474f-9619-8aacd8084dff'
report=json.loads((trial/'controller_report.json').read_bytes())
fault=report['first_fault'];cal=fault['calibration'];start=cal['stages'][-1]['wall_ns'];end=cal['request']['deadline_wall_ns']
raw=(trial/'frames.json').read_bytes();frames=json.loads(raw)['frames']
commands=sorted(report['command_publications']['rows'],key=lambda r:r['publish_finished_ns'])
ordered=report['command_publications']['joint_names']
times=[r['publish_finished_ns'] for r in commands]
names=list(report['current']['last_published_leg_targets'])
counts=Counter();selected=[];since=None;maxspan=0
for frame in frames:
 if not start<=frame['wall_ns']<=end:continue
 s=frame['samples'];j=s['joints']['data'];body=s['body']['data'];index=bisect.bisect_right(times,frame['wall_ns'])-1
 if index<0:raise RuntimeError('missing actual published reference')
 if set(ordered)!=set(names) or len(commands[index]['values'])!=len(ordered):raise RuntimeError('leg command order/dimensions')
 target=dict(zip(ordered,commands[index]['values']))
 error=max(abs(j['position'][n]-target[n]) for n in names)
 velocity=max(abs(j['velocity'][n]) for n in names)
 linear=math.hypot(*body['linear_velocity'][:2]);yaw=abs(body['angular_velocity'][2])
 bad=[k for k,v in dict(contact=not all(s['contacts']['data']['touching']),joint_error=error>.03,
  joint_speed=velocity>.02,body_speed=linear>.003,yaw_speed=yaw>.01).items() if v]
 counts.update(bad)
 if bad:since=None
 else:
  if since is None:since=frame['wall_ns']
  maxspan=max(maxspan,frame['wall_ns']-since)
 selected.append(dict(wall_ns=frame['wall_ns'],ros_ns=frame['ros_ns'],joint_error=error,
  joint_speed=velocity,body_speed=linear,yaw_speed=yaw,failed=bad,
  source_headers={k:(s[k]['stamp_ns'],s[k]['received_ns']) for k in ('joints','body','contacts')}))
result=dict(scope='independent_probe_window_not_controller_stand_since_or_acceptance',trial=trial.name,
 method_sha256=hashlib.sha256(task.read_bytes()).hexdigest(),frames_sha256=hashlib.sha256(raw).hexdigest(),
 candidate_wall_ns=start,deadline_wall_ns=end,remaining_s=(end-start)/1e9,
 selected_count=len(selected),failed_sample_counts=dict(counts),maximum_observed_healthy_span_s=maxspan/1e9,
 warning='probe cache and publication alignment are not the controller-selected cache; preserve original FAIL',samples=selected)
output=base/('g1-settle-window-'+str(uuid.uuid4())+'.json')
with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(dict(path=str(output),**{k:v for k,v in result.items() if k!='samples'})))
