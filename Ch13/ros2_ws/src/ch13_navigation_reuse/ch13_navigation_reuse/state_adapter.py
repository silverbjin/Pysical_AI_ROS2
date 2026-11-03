"""Actual free-root state to raw body and explicitly projected navigation frames."""
import math

def adapt(qpos,qvel,names,stamp_ns):
    if len(qpos)!=27 or len(qvel)!=26 or len(names)!=20 or len(set(names))!=20:raise ValueError('pinned model dimensions/joint order required')
    if not isinstance(stamp_ns,int) or stamp_ns<=0 or not all(math.isfinite(x) for x in list(qpos)+list(qvel)):raise ValueError('invalid source state/stamp')
    w,x,y,z=qpos[3:7]
    if abs(w*w+x*x+y*y+z*z-1)>1e-3:raise ValueError('invalid engine quaternion')
    yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
    roll=math.atan2(2*(w*x+y*z),1-2*(x*x+y*y));pitch=math.asin(max(-1,min(1,2*(w*y-z*x))))
    if abs(math.cos(pitch))<.01:raise ValueError('heading singularity')
    R=((1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)),(2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)),(2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)))
    body_linear=tuple(sum(R[j][i]*qvel[j] for j in range(3)) for i in range(3))
    c,s=math.cos(yaw),math.sin(yaw);ch,sh=math.cos(yaw/2),math.sin(yaw/2)
    residual=(ch*x+sh*y,ch*y-sh*x,ch*z-sh*w,ch*w+sh*z)
    return {'position':tuple(qpos[:3]),'quat_xyzw':(x,y,z,w),'body_linear':body_linear,'body_angular':tuple(qvel[3:6]),'yaw':yaw,'nav_linear':(c*qvel[0]+s*qvel[1],-s*qvel[0]+c*qvel[1],0.),'nav_yaw_rate':(math.sin(roll)*qvel[4]+math.cos(roll)*qvel[5])/math.cos(pitch),'residual_quat_xyzw':residual,'joint_positions':tuple(qpos[7:]),'joint_velocities':tuple(qvel[6:]),'stamp_ns':stamp_ns}
