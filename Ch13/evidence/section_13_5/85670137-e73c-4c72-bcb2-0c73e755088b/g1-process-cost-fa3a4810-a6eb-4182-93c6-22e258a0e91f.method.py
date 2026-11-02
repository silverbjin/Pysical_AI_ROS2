"""One-pass comparison of closed G1 calibration windows. No new experiment."""
import hashlib,json,uuid
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
names=['native-g1-gazebo-b06558d5-aa72-491f-b8e8-196f9e507802',
 'native-g1-gazebo-1e7eda2b-2dd4-474f-9619-8aacd8084dff',
 'native-g1-gazebo-03f1ca75-9497-4289-a868-a63b1b0f303a']
out=dict(scope='closed_owned_calibration_cost_not_hardware_or_pure_physics_causality',trials=[])
for name in names:
 d=base/name;r=json.loads((d/'controller_report.json').read_bytes());result=json.loads((d/'result.json').read_bytes())
 c=(r['first_fault'] or r['current'])['calibration'];phases=c['stages'];start=c['request']['wall_ns'];end=phases[-1]['wall_ns']
 ros0=c['request']['ros_ns'];ros1=phases[-1]['ros_ns'];cpu={};first={};last={};threads={};exe={}
 metric=d/'process_metrics.jsonl'
 for line in metric.open():
  p=json.loads(line);t=p['wall_ns']
  if not start<=t<=end:continue
  for m in p['members']+[p[k] for k in ('observer','full_observer') if p.get(k)]:
   pid=m['pid'];value=(t,m['user_ticks']+m['system_ticks'])
   first.setdefault(pid,value);last[pid]=value;threads[pid]=max(threads.get(pid,0),m['threads']);exe[pid]=m.get('executable',m.get('scope',''))
 for pid,(t,ticks) in first.items():
  t1,n=last[pid]
  if t1>t:cpu[pid]=dict(cpu_cores=(n-ticks)/result['cpu_clock_ticks_per_s']/((t1-t)/1e9),maximum_threads=threads[pid],executable=exe[pid])
 raw=d/'native_controls.json'
 if not raw.exists():raw=native/name/'native_controls.json'
 cost={};sha=None;errors=None
 if raw.exists():
  payload=raw.read_bytes();rows=json.loads(payload)['records'];sha=hashlib.sha256(payload).hexdigest();del payload
  a=max((v for v in rows if v['capture_ns']<=ros0),key=lambda v:v['capture_ns'])
  b=max((v for v in rows if v['capture_ns']<=ros1),key=lambda v:v['capture_ns']);errors=b['observer_work']['errors']
  for key in ('update','post_update','between_update_and_post'):
   x,y=a['observer_work'][key],b['observer_work'][key];n=y['calls']-x['calls']
   cost[key]={k:(y[k]-x[k])/n/1000 for k in ('wall_ns','cpu_ns') if k in y}
  del rows
 entry=dict(trial=name,status=result['status'],return_policy=c['vertical']['return_policy'],
  request_to_candidate_wall_s=(end-start)/1e9,request_to_candidate_ros_s=(ros1-ros0)/1e9,
  rtf=(ros1-ros0)/(end-start),remaining_wall_s=(c['request']['deadline_wall_ns']-end)/1e9,
  observer_errors=errors,observer_per_step_us=cost,raw_available=raw.exists(),
  processes=sorted(cpu.values(),key=lambda v:-v['cpu_cores']),
  source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (d/'controller_report.json',d/'result.json',metric)},
  native_controls_sha256=sha,raw_location=str(raw))
 out['trials'].append(entry)
target=base/('g1-process-cost-'+str(uuid.uuid4())+'.json')
with target.open('x') as f:json.dump(out,f,indent=2)
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(target),trials=[{k:v for k,v in r.items() if k not in ('source_sha256','processes','raw_location','native_controls_sha256')} for r in out['trials']]),indent=2))
