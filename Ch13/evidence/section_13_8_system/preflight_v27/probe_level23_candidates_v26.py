import json,os,math,sys
from pathlib import Path
import numpy as np
from ch13_navigation_reuse.scene import make_model,map_layout
from ch13_navigation_reuse.approach_geometry import footprint_clear,position_ik
root=Path(sys.argv[1]).resolve();case=Path(sys.argv[2]);out=Path(sys.argv[3]);assert not out.exists()
scenario=json.loads((case/'scenario.json').read_text())
os.environ['CH13_VALIDATION_PROFILE']='carry_v1';os.environ['CH13_VALIDATION_SCENARIO']=scenario['name']
point=np.array(json.loads((case/'last_accepted_observation.json').read_text())['point'])
with (case/'engine_observations.jsonl').open() as stream:
 for line in stream: sample=json.loads(line)
q=np.asarray(sample['qpos'])[:27]
source=root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'
model=make_model(source,'vision');free=make_model(source,'free')
fp=json.loads((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/footprint.json').read_text())['footprint']
grid=dict(width=120,height=100,resolution=.05,origin=[-2.,-2.5],data=[])
for y in range(100):
 for x in range(120):
  px=-2+(x+.5)*.05;py=-2.5+(y+.5)*.05
  grid['data'].append(100 if any(abs(px-p[0])<=z[0]+.025 and abs(py-p[1])<=z[1]+.025 for _,p,z in map_layout('vision')) else 0)
bearing=math.atan2(point[1]-q[1],point[0]-q[0]);records=[]
for label,b in [('direct'+str(o),bearing+o) for o in (0.,-.15,.15)]+[('cardinal'+str(i),i*math.pi/2) for i in range(4)]:
 distance=scenario['approach_standoff_m'];xy=point[:2]-distance*np.array([math.cos(b),math.sin(b)])
 trial=q.copy();trial[:2]=xy;trial[3:7]=[math.cos(b/2),0,0,math.sin(b/2)]
 records.append(dict(candidate=label,pose=[*xy,b],footprint=footprint_clear([*xy,b],grid,fp),
  actual_world_ik=position_ik(model,trial,point),no_obstacle_ik=position_ik(free,trial,point)))
result=dict(scope='post-exit reconstruction of saved joint state and observed point; no live authority',point=point.tolist(),records=records)
out.write_text(json.dumps(result,indent=2)+'\n')
for r in records:print(r['candidate'],'footprint',r['footprint'],'actual_world_ik',bool(r['actual_world_ik']),'free_ik',bool(r['no_obstacle_ik']))