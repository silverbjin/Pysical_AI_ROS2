"""Real MuJoCo physics. All simulator arrays stay private; no artificial attachment."""
from dataclasses import dataclass
from importlib.resources import files
import math
import numpy as np
import mujoco
from .contract import load_contract, ordered_values

@dataclass(frozen=True)
class PhysicsSnapshot:
    time: float
    positions: np.ndarray
    velocities: np.ndarray
    base_position: np.ndarray
    base_quaternion: np.ndarray
    base_tilt: float
    cube_position: np.ndarray
    tool_position: np.ndarray
    left_contact: bool
    right_contact: bool
    base_linear_velocity: np.ndarray
    base_angular_velocity: np.ndarray

class MujocoRuntime:
    def __init__(self, model_path=None):
        self.contract=load_contract()
        self._model=mujoco.MjModel.from_xml_path(str(model_path or files('ch13_sim_core').joinpath('models/integrated_robot.xml')))
        self._data=mujoco.MjData(self._model)
        def lookup(kind,name):
            value=mujoco.mj_name2id(self._model,kind,name)
            if value < 0: raise ValueError('missing simulator name '+name)
            return value
        self._joint_ids=np.array([lookup(mujoco.mjtObj.mjOBJ_JOINT,n) for n in self.contract.names])
        self._qadr=self._model.jnt_qposadr[self._joint_ids].copy()
        self._vadr=self._model.jnt_dofadr[self._joint_ids].copy()
        self._actuator_ids=np.array([lookup(mujoco.mjtObj.mjOBJ_ACTUATOR,n+'_actuator') for n in self.contract.names])
        self._base=lookup(mujoco.mjtObj.mjOBJ_BODY,'base_footprint')
        self._cube=lookup(mujoco.mjtObj.mjOBJ_BODY,'cube')
        self._tool=lookup(mujoco.mjtObj.mjOBJ_SITE,'grasp_site')
        self._cube_geom=lookup(mujoco.mjtObj.mjOBJ_GEOM,'cube_geom')
        self._fingers=[lookup(mujoco.mjtObj.mjOBJ_GEOM,'finger_'+s) for s in ('left','right')]
        self._renderer=None
        self._closed=False
        self.reset(0)

    def reset(self,seed=0):
        if self._closed: raise RuntimeError('runtime closed')
        # Seed is recorded even though this deterministic fixture introduces no noise.
        self.seed=int(seed)
        mujoco.mj_resetData(self._model,self._data)
        self._data.qpos[self._qadr]=self.contract.nominal
        self._data.ctrl[self._actuator_ids]=self.contract.nominal
        self._last_stamp=-1.
        mujoco.mj_forward(self._model,self._data)

    def apply_named_targets(self,names,positions,stamp):
        if self._closed: raise RuntimeError('runtime closed')
        values=ordered_values(names,positions,self.contract.names)
        now=float(self._data.time)
        if not math.isfinite(stamp) or stamp < self._last_stamp or stamp < now-.25 or stamp > now+.05:
            raise ValueError('stale/future/out of order command')
        self._data.ctrl[self._actuator_ids]=np.clip(values,self.contract.lower,self.contract.upper)
        self._last_stamp=stamp

    def step(self,control_steps=1):
        if self._closed: raise RuntimeError('runtime closed')
        if not isinstance(control_steps,int) or control_steps < 0: raise ValueError('invalid step count')
        mujoco.mj_step(self._model,self._data,nstep=control_steps)
        if not np.isfinite(self._data.qpos).all(): raise RuntimeError('nonfinite physics')

    def snapshot(self):
        d=self._data
        contacts=[False,False]
        for contact in d.contact:
            pair={contact.geom1,contact.geom2}
            for i,finger in enumerate(self._fingers):
                if pair == {self._cube_geom,finger} and contact.dist <= .0001: contacts[i]=True
        quat=d.xquat[self._base].copy()
        velocity=np.zeros(6)
        mujoco.mj_objectVelocity(self._model,d,mujoco.mjtObj.mjOBJ_BODY,self._base,velocity,1)
        return PhysicsSnapshot(float(d.time),d.qpos[self._qadr].copy(),d.qvel[self._vadr].copy(),d.xpos[self._base].copy(),quat,
            float(np.arccos(np.clip(1-2*(quat[1]**2+quat[2]**2),-1,1))),d.xpos[self._cube].copy(),d.site_xpos[self._tool].copy(),*contacts,velocity[3:].copy(),velocity[:3].copy())

    def render(self,path):
        from PIL import Image
        if self._renderer is None: self._renderer=mujoco.Renderer(self._model,720,960)
        camera=mujoco.MjvCamera()
        camera.lookat[:]=[.15,0,.45]; camera.distance=1.8; camera.azimuth=135; camera.elevation=-22
        self._renderer.update_scene(self._data,camera)
        Image.fromarray(self._renderer.render()).save(path)

    def close(self):
        if self._renderer is not None: self._renderer.close(); self._renderer=None
        self._closed=True
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
