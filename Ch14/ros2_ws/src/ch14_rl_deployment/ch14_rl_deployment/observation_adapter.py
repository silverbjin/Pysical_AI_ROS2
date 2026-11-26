"""Code 14-18: strict ROS envelope around the exact Ch12 ControllerCore."""
import math,time
import numpy as np
from quadruped_rl.ros_core import ControllerCore,PolicyContract,finite_vector
from .policy import contract_ok
FIELDS=[dict(slice=[0,3],meaning="body linear velocity",unit="m/s",scale=1),dict(slice=[3,6],meaning="body angular velocity",unit="rad/s",scale=1),dict(slice=[6,9],meaning="projected unit gravity",unit="1",scale=1),dict(slice=[9,12],meaning="body velocity command",unit="m/s,m/s,rad/s",scale=1),dict(slice=[12,24],meaning="joint position minus nominal",unit="rad",scale=1),dict(slice=[24,36],meaning="joint velocity",unit="rad/s",scale=1),dict(slice=[36,48],meaning="last actually applied residual",unit="1",scale=1)]
def pack_observation(*fields):
    if len(fields)!=7:raise ValueError("seven fields required")
    result=np.concatenate([finite_vector(x,n,"observation field") for x,n in zip(fields,[3,3,3,3,12,12,12])]).astype(np.float32)
    if not np.isfinite(result).all():raise ValueError("non-finite FP32 observation")
    return result
def stamp(h):
    s=h.stamp.sec+h.stamp.nanosec*1e-9
    if s<=0 or not math.isfinite(s):raise ValueError("invalid stamp")
    return s
class ObservationAdapter:
    def __init__(self,c):
        contract_ok(c)
        pc=PolicyContract(tuple(c["joint_names"]),np.array(c["nominal"]),np.array(c["joint_limits"]),np.array(c["action_scale"]),c["control_period_s"])
        self.core=ControllerCore(pc,c["sensor_timeout_s"],c["command_timeout_s"],c["max_skew_s"],c["max_target_delta_rad"])
        self.wall={};self.faults={};self.last_now=None
    def reset(self):
        self.core.reset_timing();self.wall.clear();self.faults.clear()
    def receive(self,name,msg,now,wall=None):
        wall=time.monotonic() if wall is None else wall
        try:
            if name=="imu":
                if msg.header.frame_id!="base_link" or msg.orientation_covariance[0]==-1:raise ValueError("invalid IMU frame/orientation")
                q=msg.orientation;v=msg.angular_velocity;xyzw=[q.x,q.y,q.z,q.w]
                if not np.isclose(np.linalg.norm(finite_vector(xyzw,4,"quaternion")),1.,atol=1e-3):raise ValueError("non-unit quaternion")
                self.core.update_imu(xyzw,[v.x,v.y,v.z],stamp(msg.header))
            elif name=="joints":
                if msg.header.frame_id not in ("","base_link"):raise ValueError("invalid joint frame")
                self.core.update_joints(msg.name,msg.position,msg.velocity,stamp(msg.header))
            elif name=="velocity":
                if msg.header.frame_id!="odom" or msg.child_frame_id not in ("base_link","base_footprint"):raise ValueError("invalid odom frame")
                h=msg.pose.pose.position.z
                if not math.isfinite(h) or h<.1:raise ValueError("invalid body height")
                v=msg.twist.twist.linear;self.core.update_velocity([v.x,v.y,v.z],stamp(msg.header),"body")
            elif name=="command":
                self.core.update_command([msg.linear.x,msg.linear.y,msg.angular.z],now)
            else:raise ValueError("unknown input")
            self.wall[name]=wall;self.faults.pop(name,None);return True
        except (ValueError,TypeError,IndexError) as e:
            self.faults[name]=str(e);return False
    def observation(self,now,wall=None):
        wall=time.monotonic() if wall is None else wall
        if not math.isfinite(now) or now<=0:raise RuntimeError("CLOCK_INVALID")
        if self.last_now is not None and now<self.last_now-.001:
            self.reset();self.last_now=now;raise RuntimeError("CLOCK_RESET")
        self.last_now=now
        if self.faults:raise RuntimeError("INVALID_INPUT:"+",".join(sorted(self.faults)))
        if any(wall-self.wall.get(k,-math.inf)>.5 for k in ("imu","joints","velocity")):raise RuntimeError("WALL_SENSOR_TIMEOUT")
        obs=self.core.observation(now)
        if obs.shape!=(48,) or obs.dtype!=np.float32 or not np.isfinite(obs).all():raise RuntimeError("INVALID_OBSERVATION")
        return obs
