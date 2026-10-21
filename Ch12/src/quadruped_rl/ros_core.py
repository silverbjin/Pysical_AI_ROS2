"""ROS-independent deployment contract: units, ordering, freshness and limits."""
from dataclasses import dataclass

import numpy as np


def finite_vector(value,size,name):
    result=np.asarray(value,dtype=np.float64)
    if result.shape!=(size,) or not np.isfinite(result).all():
        raise ValueError(f'{name} requires {size} finite values')
    return result.copy()


def rotation_from_xyzw(value):
    x,y,z,w=finite_vector(value,4,'quaternion xyzw')
    norm=np.linalg.norm([x,y,z,w])
    if norm<1e-6:raise ValueError('Invalid zero quaternion')
    x,y,z,w=np.array([x,y,z,w])/norm
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
        [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
        [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


@dataclass
class PolicyContract:
    joint_names:tuple
    nominal:np.ndarray
    joint_limits:np.ndarray
    action_scale:np.ndarray
    dt:float

    @classmethod
    def from_env(cls,env):
        base=env.unwrapped
        if base.control_mode!='position' or base.observation_space.shape!=(48,):
            raise ValueError('ROS controller requires 48-D position locomotion policy')
        if base.observation_mode!='locomotion':
            raise ValueError('Goal/LiDAR policies need a different ROS observation adapter')
        return cls(tuple(base.joint_names),base.nominal_joint_positions.copy(),
                   base._joint_limits.copy(),base.position_action_scale.copy(),base.dt)


class ControllerCore:
    def __init__(self,contract,sensor_timeout=.25,command_timeout=.5,max_skew=.1,
                 max_target_delta=.1):
        for value in (sensor_timeout,command_timeout,max_skew,max_target_delta):
            if not np.isfinite(value) or value<=0:raise ValueError('Timeouts/limits must be positive')
        self.contract=contract
        self.sensor_timeout=sensor_timeout
        self.command_timeout=command_timeout
        self.max_skew=max_skew
        self.max_target_delta=max_target_delta
        self.rotation=self.angular=self.positions=self.velocities=self.linear=None
        self.velocity_frame='body'
        self.stamps={}
        self.command=np.zeros(3)
        self.command_stamp=-np.inf
        self.last_action=np.zeros(12)
        self.last_target=contract.nominal.copy()

    @staticmethod
    def _stamp(value):
        if not np.isfinite(value) or value<0:raise ValueError('Invalid sensor time')
        return float(value)

    def update_imu(self,xyzw,angular,stamp):
        rotation=rotation_from_xyzw(xyzw)
        angular=finite_vector(angular,3,'body angular velocity')
        stamp=self._ordered_stamp('imu',stamp)
        self.rotation,self.angular=rotation,angular
        self.stamps['imu']=stamp

    def update_joints(self,names,positions,velocities,stamp):
        if len(names)!=len(set(names)):raise ValueError('Duplicate JointState names')
        positions=finite_vector(positions,len(names),'joint positions')
        velocities=finite_vector(velocities,len(names),'joint velocities')
        index={name:i for i,name in enumerate(names)}
        if any(name not in index for name in self.contract.joint_names):
            raise ValueError('Missing required joint names')
        order=[index[name] for name in self.contract.joint_names]
        stamp=self._ordered_stamp('joints',stamp)
        self.positions,self.velocities=positions[order],velocities[order]
        self.stamps['joints']=stamp

    def update_velocity(self,velocity,stamp,frame='body'):
        if frame not in ('body','world'):raise ValueError('velocity frame must be body/world')
        value=finite_vector(velocity,3,'linear velocity')
        stamp=self._ordered_stamp('velocity',stamp)
        self.linear,self.velocity_frame=value,frame
        self.stamps['velocity']=stamp

    def _ordered_stamp(self,name,stamp):
        stamp=self._stamp(stamp)
        if stamp<self.stamps.get(name,-np.inf)-1e-9:
            raise ValueError('Out-of-order sensor timestamp')
        return stamp

    def reset_timing(self):
        self.stamps.clear()
        self.command_stamp=-np.inf

    def update_command(self,command,stamp):
        value=finite_vector(command,3,'command')
        if np.any(np.abs(value)>3):raise ValueError('Command exceeds training bounds [-3,3]')
        stamp=self._stamp(stamp)
        if stamp<self.command_stamp-1e-9:
            raise ValueError('Out-of-order command timestamp')
        self.command=value
        self.command_stamp=stamp

    def observation(self,now):
        now=self._stamp(now)
        if len(self.stamps)!=3:raise RuntimeError('Waiting for IMU, joints and velocity')
        stamps=list(self.stamps.values())
        ages=now-np.asarray(stamps)
        if np.any(ages<-.05) or np.any(ages>self.sensor_timeout):
            raise RuntimeError('Stale/future sensor or simulation clock reset')
        if max(stamps)-min(stamps)>self.max_skew:raise RuntimeError('Sensor time skew exceeds limit')
        gravity=self.rotation.T@np.array([0.,0.,-1.])
        if gravity[2]>-np.cos(np.pi/4):raise RuntimeError('Body tilt exceeds 45 degrees')
        linear=self.rotation.T@self.linear if self.velocity_frame=='world' else self.linear
        command=(self.command if 0<=now-self.command_stamp<=self.command_timeout else np.zeros(3))
        return np.concatenate([linear,self.angular,gravity,command,
            self.positions-self.contract.nominal,self.velocities,self.last_action]).astype(np.float32)

    def sync_target(self,target):
        self.last_target=np.clip(finite_vector(target,12,'target'),
                                self.contract.joint_limits[:,0],self.contract.joint_limits[:,1])
        self.last_action=np.clip((self.last_target-self.contract.nominal)/self.contract.action_scale,-1,1)

    def process_action(self,action):
        applied=np.clip(finite_vector(action,12,'policy action'),-1,1)
        target=self.contract.nominal+self.contract.action_scale*applied
        target=np.clip(target,self.last_target-self.max_target_delta,
                       self.last_target+self.max_target_delta)
        self.sync_target(target)
        return self.last_target.copy(),self.last_action.copy()
