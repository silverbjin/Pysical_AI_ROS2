"""Closed common SHIFT->SWING windows; not hardware/physics CPU attribution."""
import hashlib,json,uuid
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
names=['native-g1-gazebo-154db0ac-0cb2-4ed8-bc02-f878557b0201',
       'native-g1-gazebo-db9883ec-1787-42fb-ba4a-c54f6946e6fb']
out=dict(scope='closed_same_phase_throughput_not_scheduling_or_hardware_causality',trials=[])
for name in names:
    d=base/name;report=json.loads((d/'controller_report.json').read_bytes());result=json.loads((d/'result.json').read_bytes())
    fault=report['first_fault'];cal=(fault or report['current'])['calibration']
    start=next(r for r in cal['stages'] if r['phase']=='SHIFT');end=next(r for r in cal['stages'] if r['phase']=='SWING')
    first={};last={};exe={};ratios=[];previous=None
    for line in (d/'process_metrics.jsonl').open():
        row=json.loads(line)
        if previous:
            dt=row['wall_ns']-previous['wall_ns'];lo=row['raw_before_ns']-previous['raw_after_ns'];hi=row['raw_after_ns']-previous['raw_before_ns']
            if lo>0:ratios.extend((dt/hi,dt/lo))
        previous=row
        if not start['wall_ns']<=row['wall_ns']<=end['wall_ns']:continue
        for p in row['members']+[row[k] for k in ('observer','full_observer') if row.get(k)]:
            key=(p['pid'],p['start_ticks']);value=(row['wall_ns'],p['user_ticks']+p['system_ticks'])
            first.setdefault(key,value);last[key]=value;exe[key]=p.get('executable',p.get('scope',''))
    processes=[]
    for key,(t,n) in first.items():
        t1,n1=last[key]
        if t1>t:processes.append(dict(executable=exe[key],cpu_cores=(n1-n)/result['cpu_clock_ticks_per_s']/((t1-t)/1e9)))
    raw=d/'native_controls.json'
    if not raw.exists():raw=native/name/'native_controls.json'
    cost={};raw_sha=None
    if raw.exists():
        payload=raw.read_bytes();raw_sha=hashlib.sha256(payload).hexdigest();records=json.loads(payload)['records'];del payload
        a=max((r for r in records if r['capture_ns']<=start['ros_ns']),key=lambda r:r['capture_ns'])
        b=max((r for r in records if r['capture_ns']<=end['ros_ns']),key=lambda r:r['capture_ns'])
        for part in ('update','post_update','between_update_and_post'):
            old,new=a['observer_work'][part],b['observer_work'][part];calls=new['calls']-old['calls']
            cost[part]={k:(new[k]-old[k])/calls/1000 for k in ('cpu_ns','wall_ns') if k in new}
        del records
    entry=dict(trial=name,status=result['status'],boot_id=result.get('boot_id'),native_physics_sha256=result.get('native_physics_sha256'),
        model_sha256=report['model_sha256'],environment=result.get('environment'),
        shift_ros_s=(end['ros_ns']-start['ros_ns'])/1e9,shift_wall_s=(end['wall_ns']-start['wall_ns'])/1e9,
        rtf=(end['ros_ns']-start['ros_ns'])/(end['wall_ns']-start['wall_ns']),
        runtime_mono_raw_bounds=[min(ratios),max(ratios)],observer_exclusive_and_interphase_us=cost,
        processes=sorted(processes,key=lambda r:-r['cpu_cores']),native_raw_available=raw.exists(),native_raw_sha256=raw_sha,
        source_sha256={name:hashlib.sha256((d/name).read_bytes()).hexdigest() for name in
            ('controller_report.json','result.json','process_metrics.jsonl')})
    out['trials'].append(entry)
target=base/('g1-shift-throughput-'+str(uuid.uuid4())+'.json')
with target.open('x') as stream:json.dump(out,stream,indent=2)
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(target),trials=[{k:v for k,v in r.items() if k not in ('source_sha256','processes','environment','native_raw_sha256')} for r in out['trials']]),indent=2))
