import json,math,sys
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);rows=[]
for uuid,target in [('dfcd2bc6-d8d1-44f3-b0cc-a0634bbba959',(2.4,1.,0.)),('272870f5-e785-4d52-8b08-e966cf65d738',(1.6,-.3,.6))]:
 folder=root/'Ch13/evidence/section_13_8_system'/uuid
 poses=[json.loads(line) for line in (folder/'ros_poses.jsonl').open()]
 samples=[dict(r,xy=math.hypot(r['x']-target[0],r['y']-target[1]),yaw_error=abs(math.atan2(math.sin(r['yaw']-target[2]),math.cos(r['yaw']-target[2])))) for r in poses]
 best=min(samples,key=lambda r:r['xy']);combined={}
 for tol in (.015,.03,.06):
  hits=[r for r in samples if r['xy']<=tol and r['yaw_error']<=.06]
  combined[str(tol)]=dict(count=len(hits),first=hits[0] if hits else None)
 row=dict(uuid=uuid,target=target,closest=best,combined_pose_hits=combined)
 rows.append(row);print(json.dumps(row))
with out.open('x') as f:json.dump(dict(scope='post-exit sampled ROS poses, counterfactual controller tolerance hits only, not new success or hypothetical dynamics proof',rows=rows),f,indent=2);f.write('\n')
