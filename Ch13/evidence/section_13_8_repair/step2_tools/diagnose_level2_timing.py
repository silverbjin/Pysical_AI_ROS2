"""Join immutable capture/observation/engine receipts around the first lease fault."""
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists();rows=[]
def load(case,name):return [json.loads(line) for line in (case/name).open()]
for uuid in ['610482f4-d941-4f52-b48f-658e05c7e397','dc937a83-0cba-48b2-b989-89361f9c5d6a','abfa9990-2960-4851-b73b-82ad28becb05']:
 c=root/'Ch13/evidence/section_13_8_system'/uuid;statuses=load(c,'manipulation_status.jsonl');fault=next(v for v in statuses if v.get('fault'));wall=fault['decision_wall'];obs=load(c,'vision_observations.jsonl');health=load(c,'camera_health.jsonl');receipts=load(c,'camera_receipts.jsonl');captures=json.loads((c/'renderer_captures.json').read_text())['captures'];engine=load(c,'engine_observations.jsonl')
 def near(values,key):return [v for v in values if wall-.5<=key(v)<=wall+.15]
 retained=next((v for v in obs if v['capture_ns']==fault['capture_ns']),None)
 row=dict(uuid=uuid,first_fault=fault,last_observation=retained,observation_age=None if retained is None else dict(capture=wall-retained['capture_wall'],receipt=wall-fault['observation_receipt_wall'],inference_start=wall-retained['inference_wall'],capture_to_inference=retained['inference_wall']-retained['capture_wall']),observations_near=[{k:v[k] for k in ['capture_ns','capture_wall','inference_wall','first_receipt_wall']} for v in near(obs,lambda v:v['inference_wall'])],health_near=near(health,lambda v:v['validation_wall']),renderer_near=near(captures,lambda v:v['capture']['capture_wall']),receipt_near=near(receipts,lambda v:v['receipt_wall']),engine_near=[{k:v.get(k) for k in ['sim_s','wall','vx','wz','mode','fault']} for v in near(engine,lambda v:v['wall'])])
 rows.append(row)
out.parent.mkdir(exist_ok=True,parents=True);out.write_text(json.dumps(dict(scope='post-exit timing joins; inference_wall is start, not publish completion',rows=rows),indent=2)+'\n')
for r in rows:
 print(r['uuid'],r['first_fault']['fault'],'decision',r['first_fault']['decision_wall'],'age',r['observation_age'],'near obs/health/render',len(r['observations_near']),len(r['health_near']),len(r['renderer_near']))
 print('OBS',r['observations_near']);print('HEALTH',r['health_near'])
