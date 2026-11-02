"""Closed same-phase host correlation; no thermal/QoS cause inferred."""
import json,hashlib,uuid
from pathlib import Path
b=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
names=[('native-g1-gazebo-0196fc1d-0391-45f2-9f0f-7e58eefb768c','host-performance-296a0bdd-7a0e-4426-92b2-253d014a2c16'),
       ('native-g1-gazebo-3f2b2183-bbde-4531-97db-a34011928008','host-performance-8c68dc11-16ae-43df-85a7-5d823a157ad8')]
out={'scope':'closed_success_failure_same_phase_host_correlation_not_causality','trials':[]}
for name,host_name in names:
 p=b/name;hp=b/host_name/'result.json';host=json.loads(hp.read_bytes())
 report=json.loads((p/'controller_report.json').read_bytes());result=json.loads((p/'result.json').read_bytes())
 metrics=[json.loads(x) for x in (p/'process_metrics.jsonl').read_text().splitlines()]
 offset=sum(m['system_ns']-m['wall_ns'] for m in metrics)/len(metrics)
 cal=(report['first_fault'] or report['current'])['calibration'];stages=cal['stages'];phases=[]
 for a,z in zip(stages,stages[1:]):
  rows=[r for r in host['samples'] if a['wall_ns']+offset<=r['utc_ns']<=z['wall_ns']+offset]
  phases.append({'phase':a['phase'],'ros_s':(z['ros_ns']-a['ros_ns'])/1e9,
    'wall_s':(z['wall_ns']-a['wall_ns'])/1e9,
    'rtf':(z['ros_ns']-a['ros_ns'])/(z['wall_ns']-a['wall_ns']),
    'host_samples':[{'performance_percent':r['performance_percent']['value'],
      'utility_percent':r['utility_percent']['value'],'ac':r['power']['ac'],
      'observer_ms':r['observer_wall_ns']/1e6} for r in rows]})
 out['trials'].append({'trial':name,'status':result['status'],'host':host_name,
   'physics_sha256':result.get('native_physics_sha256'),'model_sha256':report['model_sha256'],
   'phases':phases,'source_sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in
     (hp,p/'controller_report.json',p/'process_metrics.jsonl',p/'result.json')}})
target=b/('host-phase-comparison-'+str(uuid.uuid4())+'.json')
target.write_text(json.dumps(out,indent=2));target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(target),'trials':[{k:v for k,v in r.items() if k!='source_sha256'} for r in out['trials']]}))
