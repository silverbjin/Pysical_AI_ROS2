"""Pinned arm FK/position-only IK and conservative map footprint checks."""
import math
import numpy as np,mujoco

def tcp(model,data):return (data.xpos[model.body('link7').id]+data.xpos[model.body('link8').id])/2

def _forward(model,data):mujoco.mj_kinematics(model,data);mujoco.mj_comPos(model,data)

def arm_reach(model,q):
 d=mujoco.MjData(model);d.qpos[:]=q;_forward(model,d);names=['link2','link3','link4','link5','link6'];points=[d.xpos[model.body(n).id].copy() for n in names]+[tcp(model,d)]
 return float(sum(np.linalg.norm(b-a) for a,b in zip(points,points[1:])))

def position_ik(model,q,target):
 target=np.asarray(target,dtype=float)
 if target.shape!=(3,) or not np.isfinite(target).all():return None
 d=mujoco.MjData(model);d.qpos[:]=q;_forward(model,d)
 if np.linalg.norm(target-d.xpos[model.body('link2').id])>arm_reach(model,q)+.03:return None
 ids=np.array([model.joint('joint'+str(i)).id for i in range(1,7)]);qa=model.jnt_qposadr[ids];va=model.jnt_dofadr[ids];limits=model.jnt_range[ids];jac=np.zeros((3,model.nv));body=model.body('link6').id
 seeds=[np.asarray(q)[qa].copy(),[0,1.5,-1.5,0,0,0],[0,2.5,-1.2,0,-.8,0],[0,2.,-.6,0,-.5,0],[0,1.,-2.2,0,.5,0]]
 for seed in seeds:
  d.qpos[:]=q;d.qpos[qa]=np.clip(seed,limits[:,0],limits[:,1])
  for iteration in range(100):
   _forward(model,d);point=tcp(model,d);error=target-point;residual=float(np.linalg.norm(error))
   if residual<=.02:
    mujoco.mj_forward(model,d);collision=False
    for contact in d.contact:
     a,b=map(int,contact.geom);an=model.body(int(model.geom_bodyid[a])).name;bn=model.body(int(model.geom_bodyid[b])).name;arm=lambda n:n.startswith('link')
     if not (arm(an) or arm(bn)) or {an,bn}<={'link7','link8'}:continue
     ga=model.geom(a).name;gb=model.geom(b).name
     if (ga=='reuse_target' and bn in ['link6','link7','link8']) or (gb=='reuse_target' and an in ['link6','link7','link8']):continue
     collision=True;break
    if not collision:return {'q_arm':d.qpos[qa].copy().tolist(),'residual_m':residual,'joint_limits_ok':True,'collision_free':True}
    break
   mujoco.mj_jac(model,d,jac,None,point,body);j=jac[:,va];delta=j.T@np.linalg.solve(j@j.T+.001*np.eye(3),error);d.qpos[qa]=np.clip(d.qpos[qa]+np.clip(delta,-.15,.15),limits[:,0],limits[:,1])
 return None

def footprint_clear(pose,grid,footprint):
 x,y,yaw=pose;c,s=math.cos(yaw),math.sin(yaw);r=np.array([[c,-s],[s,c]]);poly=np.array(footprint)@r.T+[x,y];resolution=grid['resolution'];ox,oy=grid['origin'];lo=np.floor((poly.min(axis=0)-[ox,oy])/resolution).astype(int);hi=np.floor((poly.max(axis=0)-[ox,oy])/resolution).astype(int)
 if min(lo)<0 or hi[0]>=grid['width'] or hi[1]>=grid['height']:return False
 axes=[np.array([1.,0.]),np.array([0.,1.]),r[:,0],r[:,1]]
 for iy in range(lo[1],hi[1]+1):
  for ix in range(lo[0],hi[0]+1):
   if grid['data'][iy*grid['width']+ix]==0:continue
   cell=np.array([[ix,iy],[ix+1,iy],[ix+1,iy+1],[ix,iy+1]])*resolution+[ox,oy]
   if all(not (max(poly@axis)<min(cell@axis) or max(cell@axis)<min(poly@axis)) for axis in axes):return False
 return True

def candidates(model,q,point,grid,footprint):
 reach=arm_reach(model,q);result=[];point=np.asarray(point);initial=np.asarray(q);base=initial[:2]
 for distance in [reach-.15,reach-.25,reach-.35]:
  if distance<=max(p[0] for p in footprint)+.08:continue
  for angle in [0.,-.15,.15]:
   bearing=math.atan2(point[1]-base[1],point[0]-base[0])+angle;xy=point[:2]-distance*np.array([math.cos(bearing),math.sin(bearing)]);heading=math.atan2(point[1]-xy[1],point[0]-xy[0]);pose=[float(xy[0]),float(xy[1]),heading]
   if not footprint_clear(pose,grid,footprint):continue
   trial=initial.copy();trial[:2]=xy;trial[3:7]=[math.cos(heading/2),0.,0.,math.sin(heading/2)];ik=position_ik(model,trial,point)
   if ik is not None:result.append({'pose':pose,'distance_from_observed_surface_m':distance,'ik':ik,'lower_bound_path_m':float(np.linalg.norm(xy-base))})
 return sorted(result,key=lambda x:x['lower_bound_path_m'])
