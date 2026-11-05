import json,math
from pathlib import Path
root=Path.cwd();case=root/'Ch13/evidence/section_13_8_system/1d76511d-810d-41bb-a3c4-1db69ecb15bc'
rows=[]
for line in (case/'engine_observations.jsonl').open():
 r=json.loads(line);q=r['qpos'];w,x,y,z=q[3:7];yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));error=math.hypot(q[0]-1.9,q[1]-1.)
 rows.append(dict(sim_s=r['sim_s'],wall=r['wall'],x=q[0],y=q[1],yaw=yaw,error=error,vx=r['vx'],wz=r['wz']))
closest=min(rows,key=lambda r:r['error']);first=next((r for r in rows if r['error']<.015),None)
out=dict(scope='saved survey goal (1.9,1,0), no engine',closest=closest,first_xy=first,near_first=[] if first is None else [r for r in rows if abs(r['sim_s']-first['sim_s'])<1.],last=rows[-1])
p=root/'Ch13/evidence/section_13_8_repair/step4_survey_v31.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='near_first'},indent=2))