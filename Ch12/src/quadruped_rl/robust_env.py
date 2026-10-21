"""Opt-in dynamics, sensor, latency and world-force perturbations (section 12.7).

The underlying task owns physics and reward semantics. Queued observations are
complete historical frames: their last-action field is the action actually
applied at that frame's timestamp, never the newly commanded action.
"""
from collections import deque
from numbers import Integral

import gymnasium as gym
import mujoco
import numpy as np

from .locomotion_env import QuadrupedLocomotionEnv


class RobustQuadrupedEnv(gym.Wrapper):
    """Default: mass/inertia ±20%, friction ×.5..1.5, motor strength ±10%.

    Delay units are control transitions (default 2 × .02 s). Sensor standard
    deviations are m/s, rad/s, unit gravity, rad and rad/s respectively. LiDAR
    noise remains the avoidance task's independently configured metre noise.
    Set ``enabled=False`` for a bitwise baseline-equivalent ablation.
    """

    def __init__(self, env=None, *, task='locomotion', enabled=True,
                 randomize_dynamics=True, sensor_noise=True,
                 action_delay=2, observation_delay=2, push_probability=.01,
                 push_force=50., noise_std=None, **env_kwargs):
        for name, value in [('action_delay',action_delay),('observation_delay',observation_delay)]:
            if isinstance(value,bool) or not isinstance(value,Integral) or value < 0:
                raise ValueError(f'{name} must be a nonnegative integer')
        if (not np.isfinite(push_probability) or not 0 <= push_probability <= 1
                or not np.isfinite(push_force) or push_force < 0):
            raise ValueError('push_probability must be [0,1]; push_force finite and nonnegative')
        factories = {'locomotion':QuadrupedLocomotionEnv}
        if task == 'goal':
            from .goal_env import QuadrupedGoalEnv
            factories[task] = QuadrupedGoalEnv
        if task == 'avoidance':
            from .avoidance_env import QuadrupedAvoidanceEnv
            factories[task] = QuadrupedAvoidanceEnv
        if task not in factories:
            raise ValueError('task must be locomotion, goal or avoidance')
        if env is not None and env_kwargs:
            raise ValueError('Pass an env OR task constructor kwargs')
        noise = dict(linear_velocity=.05,angular_velocity=.02,gravity=.01,
                     joint_position=.005,joint_velocity=.02)
        if noise_std is not None:
            if not isinstance(noise_std,dict) or set(noise_std)-set(noise):
                raise ValueError('noise_std keys must name physical sensor fields')
            noise.update(noise_std)
        if any(not np.isfinite(v) or v < 0 for v in noise.values()):
            raise ValueError('noise standard deviations must be finite and nonnegative')
        super().__init__(factories[task](**env_kwargs) if env is None else env)
        core = self.unwrapped
        if not isinstance(core,QuadrupedLocomotionEnv):
            raise TypeError('RobustQuadrupedEnv requires a Locomotion/Goal/Avoidance task')
        self.enabled = bool(enabled)
        self.randomize_dynamics = bool(randomize_dynamics)
        self.sensor_noise = bool(sensor_noise)
        self.action_delay = int(action_delay) if enabled else 0
        self.observation_delay = int(observation_delay) if enabled else 0
        self.push_probability = float(push_probability)
        self.push_force = float(push_force)
        self.noise_std = noise
        self._actions = deque()
        self._observations = deque()
        self._cached_obs = None
        self._ready = False
        m = core.model
        # body_rootid excludes mocap targets, kinematic boxes and world geometry.
        self.robot_body_ids = np.flatnonzero((m.body_rootid == core._base_id)
            & (m.body_mocapid < 0) & (m.body_mass > 0))
        self._friction_ids = np.array(sorted({core._ground_geom,*core._foot_geoms}))
        self._originals = {name:getattr(m,name).copy() for name in
            ['body_mass','body_inertia','geom_friction','actuator_gainprm',
             'actuator_biasprm','actuator_forcerange']}
        self._original_torque_limits = core.torque_limits.copy()
        for array in self._originals.values():
            array.flags.writeable = False
        self._original_torque_limits.flags.writeable = False
        self._domain = {}

    @property
    def original_friction(self):
        return self._originals['geom_friction'].copy()

    def _randomize_model(self):
        core, rng = self.unwrapped, self.np_random
        model = core.model
        # Restore immutable compiled originals before every draw; never multiply
        # last episode's values. One factor per link preserves inertia scaling.
        for name, original in self._originals.items():
            getattr(model,name)[:] = original
        mass = rng.uniform(.8,1.2,len(self.robot_body_ids))
        friction = float(rng.uniform(.5,1.5))
        strength = float(rng.uniform(.9,1.1))
        ids = self.robot_body_ids
        model.body_mass[ids] = self._originals['body_mass'][ids]*mass
        model.body_inertia[ids] = self._originals['body_inertia'][ids]*mass[:,None]
        # MuJoCo's equal-priority contact friction uses max mixing. Scale both
        # floor and feet so lowering floor friction actually lowers the contact.
        model.geom_friction[self._friction_ids] = self._originals['geom_friction'][self._friction_ids]*friction
        aids = core._actuator_ids
        for name in ['actuator_gainprm','actuator_biasprm','actuator_forcerange']:
            getattr(model,name)[aids] = self._originals[name][aids]*strength
        # Torque controls already pass through randomized actuator gain. Keep
        # their nominal input conversion unchanged to avoid strength squared;
        # the physical forcerange above still scales the actual saturation.
        core.torque_limits[:] = (self._original_torque_limits if core.control_mode == 'torque'
                                 else self._original_torque_limits*strength)
        # mj_setConst uses its data as scratch and sets qpos to model.qpos0.
        # Recompute model constants with a disposable data object so the task's
        # seeded reset pose/velocity, mocap layout and controls remain intact.
        mujoco.mj_setConst(model,mujoco.MjData(model))
        mujoco.mj_forward(model,core.data)
        self._domain = dict(robot_body_ids=ids.tolist(),mass_factors=mass.tolist(),
                            friction_factor=friction,actuator_strength=strength)

    def _measure(self, observation):
        obs = observation.copy()
        if self.enabled and self.sensor_noise:
            for key, field in [('linear_velocity',slice(0,3)),('angular_velocity',slice(3,6)),
                    ('gravity',slice(6,9)),('joint_position',slice(12,24)),
                    ('joint_velocity',slice(24,36))]:
                std = self.noise_std[key]
                if std:
                    obs[field] += self.np_random.normal(0,std,obs[field].shape)
            magnitude = np.linalg.norm(obs[6:9])
            obs[6:9] = obs[6:9]/magnitude if magnitude > 1e-12 else observation[6:9]
        return obs

    def _get_obs(self):
        """Return the cached policy frame; reading it never resamples noise."""
        if self._cached_obs is None:
            raise RuntimeError('Call reset before reading observations')
        return self._cached_obs.copy()

    def reset(self, *, seed=None, options=None):
        self._ready = False
        core = self.unwrapped
        core.data.xfrc_applied.fill(0)
        observation, info = self.env.reset(seed=seed,options=options)
        self._domain = {}
        if self.enabled and self.randomize_dynamics:
            self._randomize_model()
            observation = core._get_obs()
        core.data.xfrc_applied.fill(0)
        self._actions.clear()
        self._actions.extend(np.zeros(self.action_space.shape) for _ in range(self.action_delay))
        measured = self._measure(observation)
        self._observations.clear()
        self._observations.extend(measured.copy() for _ in range(self.observation_delay))
        self._cached_obs = measured.copy()
        self._ready = True
        info = dict(info,domain_randomization=dict(self._domain),
                    action_delay_steps=self.action_delay,observation_delay_steps=self.observation_delay)
        return self._get_obs(),info

    def step(self, action):
        if not self._ready or self.unwrapped._needs_reset:
            raise RuntimeError('Call reset before step and after episode end')
        command = np.asarray(action,dtype=np.float64)
        if command.shape != self.action_space.shape or not np.isfinite(command).all():
            raise ValueError('action must contain 12 finite numbers with shape (12,)')
        clipped = np.clip(command,-1,1)
        self._actions.append(clipped.copy())
        delayed = self._actions.popleft()
        force = np.zeros(3)
        if self.enabled and self.push_probability and self.np_random.random() < self.push_probability:
            force = self.np_random.uniform(-self.push_force,self.push_force,3)
        data = self.unwrapped.data
        data.xfrc_applied.fill(0)
        # mj_step reads this world-frame wrench on every fixed physics substep.
        data.xfrc_applied[self.unwrapped._base_id,:3] = force
        try:
            observation,reward,terminated,truncated,info = self.env.step(delayed)
        except BaseException:
            self._ready = False
            raise
        finally:
            data.xfrc_applied.fill(0)
        self._observations.append(self._measure(observation))
        self._cached_obs = self._observations.popleft()
        info = dict(info,commanded_action=command.tolist(),delayed_action=delayed.tolist(),
                    action_clipped=bool(np.any(command != clipped)),
                    external_force_world=force.tolist(),action_delay_steps=self.action_delay,
                    observation_delay_steps=self.observation_delay)
        return self._get_obs(),reward,terminated,truncated,info
