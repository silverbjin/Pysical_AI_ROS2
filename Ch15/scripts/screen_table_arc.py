import json,zipfile,math,sys,hashlib
from pathlib import Path
import numpy as np
from arc_straight_profile import *
from table_approach_contract import world

def pose(q):return q[0],q[1],math.atan2(2*(q[3]*q[6]+q[4]*q[5]),1-2*(q[5]**2+q[6]**2))
def cmd(p,vg=.25,wg=.8):
 err,along,cross=arc_error(p)
 if -p[2]<-.08 or err>.05:return None
 if -p[2]>=ANGLE-ARC_STOP_LEAD:return (0.,0.)
 return clip(ARC_V_FEED+.6*along+vg*cross,0,ARC_V_MAX),clip(ARC_W+wg*cross,ARC_W,ARC_W_MAX)
def screen(z,vg,wg):
 r=json.loads(z.read('case/native/segment_result.json'));p=r['phases'][2];e=r['entry_goal'];rows=[json.loads(l) for l in z.read('case/native/engine_observations.jsonl').splitlines()];a=[]
 for row in rows:
  if p['release_sim_ns']/1e9-1e-7<=row['sim_s']<=p['end_sim_ns']/1e9+1e-7:
   q=local(pose(row['qpos']),e);th=-q[2]
   if not a or th>a[-1][0]:a.append((th,row['sim_s'],q[0],q[1]))
 a=np.array(a);steps=np.linspace(a[0,0],a[-1,0],max(1,math.ceil((a[-1,0]-a[0,0])/.01))+1);pts=np.column_stack([steps]+[np.interp(steps,a[:,0],a[:,i]) for i in (1,2,3)])
 x,y=pts[0,2:];elapsed=0.;maxerr=0.;rej=False
 for A,B in zip(pts,pts[1:]):
  th,ta,ox,oy=A;dt=B[1]-ta;dth=B[0]-th;old=(ox,oy,-th);new=(x,y,-th);co=cmd(old);cn=cmd(new,vg,wg)
  if co is None or cn is None or dt<=0:rej=True;break
  w=-dth/dt+1.08*(cn[1]-co[1]);
  if w>=-.01:rej=True;break
  dnew=-dth/w
  # measured body increment, perturbed by local linear forward gain
  theta=-(th+B[0])/2;c,s=math.cos(theta),math.sin(theta);dx,dy=B[2]-ox,B[3]-oy
  vx=(c*dx+s*dy)/dt+.844*(cn[0]-co[0]);vy=(-s*dx+c*dy)/dt
  x+=(c*vx-s*vy)*dnew;y+=(s*vx+c*vy)*dnew;elapsed+=dnew;maxerr=max(maxerr,arc_error((x,y,-B[0]))[0])
 qend=local(p['end_pose'],e);qsettle=local(p['settled_pose'],e);x+=qsettle[0]-qend[0];y+=qsettle[1]-qend[1];h=qsettle[2];g=world((x,y,h),e)
 return dict(vg=vg,wg=wg,xy_m=math.dist((x,y),arc_point(ANGLE)),yaw_rad=abs(h+ANGLE),final_world=g,elapsed_sim_s=elapsed,maxerr=maxerr,rejected=rej)
def main(*paths):
 results=[]
 for path in paths:
  with zipfile.ZipFile(path) as z:
   manifest=z.read('sha256sums.txt').decode().splitlines()
   for line in manifest:
    digest,name=line.split(maxsplit=1);name=name.lstrip('*').removeprefix('./')
    if hashlib.sha256(z.read(name)).hexdigest()!=digest:raise ValueError('member mismatch '+name)
   results.append(dict(archive=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),members=len(manifest),candidates=[screen(z,v,w) for v,w in [(.25,.8),(.25,1.),(.25,1.15),(.25,1.3),(.35,.8),(.35,1.),(.45,.8)]]))
 print(json.dumps(dict(scope='angle-resampled recorded displacement sensitivity; not physical prediction',cases=results),indent=2,allow_nan=False))
if __name__=='__main__':main(*sys.argv[1:])
