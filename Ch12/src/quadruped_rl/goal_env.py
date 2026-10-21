"""Goal-conditioned navigation, atomic goal changes and bounded visual trails."""
from collections import deque
import math
from numbers import Integral

import mujoco
import numpy as np

from .locomotion_env import QuadrupedLocomotionEnv


class QuadrupedGoalEnv(QuadrupedLocomotionEnv):
    """45 proprioceptive values + [distance, sin(heading), cos(heading)].

    Progress is distance reduction shaping, not discounted policy-invariant
    potential shaping. A goal change is applied only after the old-goal reward.
    """
    model_files = {'position': 'quadruped_goal.xml'}

    def __init__(self, render_mode=None, radius_range=(2.,3.),arrival_radius=.3,
                 goal_mode='resample',progress_scale=50.,arrival_bonus=10.,
                 trail_capacity=256,trail_seconds=5.,**kwargs):
        bounds = np.asarray(radius_range,dtype=float)
        if (bounds.shape != (2,) or not np.isfinite(bounds).all()
                or bounds[0] <= 0 or bounds[0] > bounds[1]):
            raise ValueError('radius_range must be ordered positive radii')
        if (not np.isfinite(arrival_radius) or not 0 < arrival_radius < bounds[0]):
            raise ValueError('arrival_radius must be positive and smaller than minimum radius')
        if goal_mode not in ('resample','terminate'):
            raise ValueError('goal_mode must be resample or terminate')
        if (not np.isfinite(progress_scale) or progress_scale < 0
                or not np.isfinite(arrival_bonus) or arrival_bonus < 0):
            raise ValueError('Reward scales must be finite and nonnegative')
        if (isinstance(trail_capacity,bool) or not isinstance(trail_capacity,Integral)
                or not 1 <= trail_capacity <= 1000
                or not np.isfinite(trail_seconds) or trail_seconds <= 0):
            raise ValueError('trail_capacity must be 1..1000 and trail_seconds positive')
        if kwargs.get('control_mode','position') != 'position':
            raise ValueError('Goal task uses position control')
        if 'command' in kwargs or 'command_ranges' in kwargs:
            raise ValueError('Goal task replaces velocity commands with goal features')
        self.radius_range = bounds.copy()
        self.arrival_radius = float(arrival_radius)
        self.goal_mode = goal_mode
        self.progress_scale = float(progress_scale)
        self.arrival_bonus = float(arrival_bonus)
        self.trail_seconds = float(trail_seconds)
        self._trajectory = deque(maxlen=int(trail_capacity))
        self._target_pos = np.zeros(3)
        self._prev_dist = 0.
        self.goals_reached = 0
        self._in_transition = False
        super().__init__(render_mode=render_mode,command=[0,0,0],**kwargs)
        self.observation_mode = 'goal'
        target_id = self.model.body('target').id
        self._target_mocap_id = int(self.model.body_mocapid[target_id])
        if self._target_mocap_id < 0:
            raise ValueError('target must be a mocap body')

    @property
    def target_pos(self):
        return self._target_pos.copy()

    @property
    def trajectory(self):
        return [(stamp,pos.copy()) for stamp,pos in self._trajectory]

    @staticmethod
    def quat_to_yaw(quat):
        quat = np.asarray(quat, dtype=np.float64)
        if quat.shape != (4,) or not np.isfinite(quat).all():
            raise ValueError('yaw quaternion must have four finite wxyz elements')
        norm = float(np.linalg.norm(quat))
        if norm < 1e-6:
            raise ValueError('yaw quaternion must have nonzero norm')
        w,x,y,z = quat/norm
        return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))

    def goal_features(self):
        delta = self._target_pos[:2]-self.data.qpos[:2]
        distance = float(np.linalg.norm(delta))
        if distance < 1e-12:
            return np.array([distance,0.,1.])
        yaw = self.quat_to_yaw(self.data.qpos[3:7])
        heading = math.atan2(delta[1],delta[0])-yaw
        return np.array([distance,math.sin(heading),math.cos(heading)])

    def _get_obs(self):
        proprio = super()._get_obs()
        proprio[9:12] = self.goal_features()
        return proprio

    @staticmethod
    def _validate_target(target):
        point = np.asarray(target,dtype=float)
        if point.shape not in ((2,),(3,)) or not np.isfinite(point).all() or np.any(np.abs(point)>1e4):
            raise ValueError('target must be finite world xy or xyz within +/-10000m')
        return np.array([point[0],point[1],.2])

    def set_target(self,target):
        point = self._validate_target(target)
        self._target_pos[:] = point
        self.data.mocap_pos[self._target_mocap_id] = point
        mujoco.mj_forward(self.model,self.data)
        self._prev_dist = self.goal_features()[0]

    def reset_target(self):
        rho = self.np_random.uniform(*self.radius_range)
        phi = self.np_random.uniform(-math.pi,math.pi)
        self.set_target(self.data.qpos[:2]+rho*np.array([math.cos(phi),math.sin(phi)]))

    def reset(self,*,seed=None,options=None):
        options = {} if options is None else options
        if not isinstance(options,dict) or set(options)-{'target'}:
            raise ValueError('reset options only supports target')
        point = self._validate_target(options['target']) if 'target' in options else None
        self._in_transition = True
        try:
            _,info = super().reset(seed=seed)
        finally:
            self._in_transition = False
        self.goals_reached = 0
        self._trajectory.clear()
        if point is not None:
            self.set_target(point)
        else:
            self.reset_target()
        self._record_position()
        info.pop('command',None)
        info.update(target=self.target_pos.tolist(),distance=float(self._prev_dist))
        if self.render_mode == 'human':
            self.render()
        return self._get_obs(),info

    def _compute_reward(self,applied,previous_action,terminated):
        terms = super()._compute_reward(applied,previous_action,terminated)
        terms.pop('linear_tracking')
        terms.pop('yaw_tracking')
        distance = self.goal_features()[0]
        success = bool(not terminated and distance < self.arrival_radius)
        terms['progress'] = 0. if terminated else self.progress_scale*(self._prev_dist-distance)
        terms['arrival'] = self.arrival_bonus if success else 0.
        if not all(math.isfinite(value) for value in terms.values()):
            raise FloatingPointError('Non-finite goal reward')
        self._goal_event = dict(is_success=success,distance=float(distance),
            evaluated_target=self.target_pos.tolist(),progress_distance=float(self._prev_dist-distance))
        return terms

    def _record_position(self):
        self._trajectory.append((float(self.data.time),self.data.qpos[:3].copy()))
        while self._trajectory and self.data.time-self._trajectory[0][0] > self.trail_seconds:
            self._trajectory.popleft()

    def step(self,action):
        self._in_transition = True
        try:
            _,reward,terminated,truncated,info = super().step(action)
        finally:
            self._in_transition = False
        event = self._goal_event
        self._prev_dist = event['distance']
        if event['is_success']:
            self.goals_reached += 1
            if self.goal_mode == 'terminate':
                terminated = True
                self._needs_reset = True
            elif not truncated:
                self.reset_target()
        self._record_position()
        info.pop('command',None)
        info.update(event,goals_reached=self.goals_reached,target=self.target_pos.tolist(),
                    next_distance=float(self._prev_dist),episode_success=self.goals_reached>0)
        if self.render_mode == 'human':
            self.render()
        return self._get_obs(),reward,terminated,truncated,info

    def _add_trail(self,scene):
        for _,pos in self._trajectory:
            if scene.ngeom >= scene.maxgeom:
                break
            mujoco.mjv_initGeom(scene.geoms[scene.ngeom],mujoco.mjtGeom.mjGEOM_SPHERE,
                np.array([.02,0,0]),np.array([pos[0],pos[1],.025]),np.eye(3).ravel(),
                np.array([.05,.2,1.,.8],dtype=np.float32))
            scene.ngeom += 1

    def _fit_camera(self,camera):
        """Keep both the robot and current goal visible, including after retarget."""
        camera.type = mujoco.mjtCamera.mjCAMERA_FREE
        camera.lookat[:] = [*(.5*(self.data.qpos[:2]+self._target_pos[:2])),.15]
        camera.distance = max(3.,1.7*self.goal_features()[0]+1.)
        camera.azimuth = 135.
        camera.elevation = -55.

    def render(self):
        if self._in_transition:
            return None
        if self.render_mode == 'rgb_array':
            if self._renderer is None:
                self._renderer = mujoco.Renderer(self.model,height=480,width=640)
            camera = mujoco.MjvCamera()
            self._fit_camera(camera)
            self._renderer.update_scene(self.data,camera=camera)
            self._add_trail(self._renderer.scene)
            return self._renderer.render()
        if self.render_mode == 'human':
            if self._viewer is None:
                from mujoco import viewer
                self._viewer = viewer.launch_passive(self.model,self.data)
            if self._viewer.is_running():
                with self._viewer.lock():
                    self._fit_camera(self._viewer.cam)
                    self._viewer.user_scn.ngeom = 0
                    self._add_trail(self._viewer.user_scn)
                self._viewer.sync()
        return None
