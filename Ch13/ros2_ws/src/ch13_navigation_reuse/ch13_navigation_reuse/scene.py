"""Opt-in educational world; upstream robot dynamics and files stay unchanged."""
import math,os
import numpy as np
import mujoco
from scipy.spatial.transform import Rotation
SCAN_POS=np.array([.4,0.,.25]);CAM_POS=np.array([.4,0.,.25])
OPTICAL_R=np.array([[0.,0.,1.],[-1.,0.,0.],[0.,-1.,0.]])
def layout(profile):
 walls=[('wall_left',[-2.,0.,.4],[.05,2.5,.4]),('wall_right',[4.,0.,.4],[.05,2.5,.4]),('wall_bottom',[1.,-2.5,.4],[3.,.05,.4]),('wall_top',[1.,2.5,.4],[3.,.05,.4])]
 if profile=='obstacle':walls.append(('obstacle',[1.2,0.,.4],[.14,.23,.4]))
 if profile=='blocked':walls.append(('barrier',[1.2,0.,.4],[.14,2.5,.4]))
 if profile=='vision':walls.extend([('target',[1.8,0.,.55],[.05,.05,.05]),('pedestal',[1.8,0.,.25],[.035,.035,.25])])
 if profile=='vision' and os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1':
  walls.append(('receiving_support',[-.55,0.,.25],[.045,.045,.25]))
 return walls

def make_model(source,profile,spec_hook=None):
 if profile not in ('free','obstacle','blocked','vision'):raise ValueError('unknown educational scene')
 s=mujoco.MjSpec.from_file(str(source))
 for geom in list(s.worldbody.geoms):
  if geom.name!='floor':s.delete(geom)
 for name,pos,size in layout(profile):s.worldbody.add_geom(name='reuse_'+name,type=mujoco.mjtGeom.mjGEOM_BOX,pos=pos,size=size,group=5,rgba=[.9,.02,.02,1.] if name=='target' else [.3,.35,.4,1.])
 # MuJoCo camera has right/up/back axes; ROS optical is right/down/forward.
 camera_r=OPTICAL_R@np.diag([1.,-1.,-1.]);quat=np.roll(Rotation.from_matrix(camera_r).as_quat(),1)
 s.body('base').add_camera(name='reuse_rgbd',pos=CAM_POS,quat=quat,fovy=55.)
 if spec_hook is not None:spec_hook(s)
 return s.compile()

def ray_scan(model,data,count=181):
 mujoco.mj_kinematics(model,data) # ray origin and header use the same post-integration state
 base=model.body('base').id;r=data.xmat[base].reshape(3,3);origin=data.xpos[base]+r@SCAN_POS
 groups=np.zeros(6,dtype=np.uint8);groups[5]=1;hit=np.zeros(1,dtype=np.int32);result=[]
 for angle in np.linspace(-math.pi,math.pi,count):
  direction=r@np.array([math.cos(angle),math.sin(angle),0.]);distance=mujoco.mj_ray(model,data,origin,direction,groups,1,-1,hit)
  result.append(float(distance) if 0.05<=distance<=4. else float('inf'))
 return result

def footprint(model,snapshots,margin=.04):
 data=mujoco.MjData(model);points=[]
 signs=np.array([[i,j,k] for i in [-1,1] for j in [-1,1] for k in [-1,1]])
 for q in snapshots:
  data.qpos[:]=q;mujoco.mj_kinematics(model,data);yaw=math.atan2(2*(q[3]*q[6]+q[4]*q[5]),1-2*(q[5]**2+q[6]**2));r=Rotation.from_euler('z',yaw).as_matrix()
  for g in range(model.ngeom):
   if model.geom_bodyid[g]==0 or not (model.geom_contype[g] or model.geom_conaffinity[g]):continue
   center,half=model.geom_aabb[g,:3],model.geom_aabb[g,3:];local=center+signs*half;world=local@data.geom_xmat[g].reshape(3,3).T+data.geom_xpos[g];points.extend((world-np.array(q[:3]))@r)
 a=np.asarray(points);lo=a[:,:2].min(axis=0)-margin;hi=a[:,:2].max(axis=0)+margin
 return [[float(lo[0]),float(lo[1])],[float(hi[0]),float(lo[1])],[float(hi[0]),float(hi[1])],[float(lo[0]),float(hi[1])]]
