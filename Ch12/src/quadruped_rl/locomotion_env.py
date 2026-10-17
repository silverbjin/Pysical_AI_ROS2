"""Command-conditioned proprioception and inspectable rewards for section 12.3."""
import math

import gymnasium as gym
import numpy as np

from .rewards import RewardConfig, compute_reward_terms
from .training_env import QuadrupedTrainingEnv


class QuadrupedLocomotionEnv(QuadrupedTrainingEnv):
    """48 observations, body-frame commands and residual position control by default."""

    def __init__(self, render_mode=None, command=None, command_ranges=None,
                 action_scale=.35, reward_config=None, max_tilt_degrees=45, **kwargs):
        if 'observation_mode' in kwargs:
            raise ValueError("Section 12.3 has a fixed 48-dimensional observation")
        if not np.isfinite(action_scale) or not 0 < action_scale <= 1:
            raise ValueError("action_scale must be in (0, 1] radians")
        if not np.isfinite(max_tilt_degrees) or not 0 < max_tilt_degrees <= 90:
            raise ValueError("max_tilt_degrees must be in (0, 90]")
        self.reward_config = RewardConfig() if reward_config is None else reward_config
        if not isinstance(self.reward_config, RewardConfig):
            raise TypeError("reward_config must be RewardConfig")
        self._configured_command = self._validate_command(
            (kwargs.get('target_velocity', .5), 0, 0) if command is None else command)
        self._command = self._configured_command.copy()
        self._command_ranges = None
        if command_ranges is not None:
            bounds = np.asarray(command_ranges, dtype=np.float64)
            if (bounds.shape != (3, 2) or not np.isfinite(bounds).all()
                    or np.any(bounds[:, 0] > bounds[:, 1]) or np.any(np.abs(bounds) > 3)):
                raise ValueError("command_ranges must be ordered (3, 2) bounds within [-3, 3]")
            self._command_ranges = bounds.copy()
        super().__init__(render_mode=render_mode, **kwargs)
        self.position_action_scale.fill(float(action_scale))
        self._tilt_cosine = math.cos(math.radians(max_tilt_degrees))
        self._foot_geoms = {self.model.geom(f'{leg}_foot_collision').id
                            for leg in ('fr', 'fl', 'rr', 'rl')}
        self._step_bad_contacts = set()
        self._reward_raw = {}
        self.observation_mode = 'locomotion'
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(48,), dtype=np.float32)

    @staticmethod
    def _validate_command(value):
        result = np.asarray(value, dtype=np.float64)
        if result.shape != (3,) or not np.isfinite(result).all() or np.any(np.abs(result) > 3):
            raise ValueError("command must contain vx, vy, yaw rate in [-3, 3]")
        return result.copy()

    @property
    def command(self):
        return self._command.copy()

    @property
    def default_joint_pos(self):
        return self.nominal_joint_positions.copy()

    @property
    def last_action(self):
        return self._previous_action.copy()

    def set_command(self, command):
        self._command = self._validate_command(command)

    def get_base_linear_velocity(self):
        rotation = self.data.xmat[self._base_id].reshape(3, 3)
        return rotation.T @ self.data.qvel[:3]

    def get_base_angular_velocity(self):
        return self.data.qvel[3:6].copy()

    def get_gravity_vector(self):
        gravity = self.model.opt.gravity
        magnitude = np.linalg.norm(gravity)
        if not np.isfinite(magnitude) or magnitude <= 0:
            raise ValueError("A finite nonzero gravity vector is required")
        rotation = self.data.xmat[self._base_id].reshape(3, 3)
        return rotation.T @ (gravity/magnitude)

    def _get_obs(self):
        return np.concatenate([self.get_base_linear_velocity(), self.get_base_angular_velocity(),
            self.get_gravity_vector(), self._command,
            self.data.qpos[self._qpos_ids]-self.nominal_joint_positions,
            self.data.qvel[self._qvel_ids], self._previous_action]).astype(np.float32)

    def reset(self, *, seed=None, options=None):
        options = {} if options is None else options
        if not isinstance(options, dict) or set(options)-{'command'}:
            raise ValueError("reset options only supports 'command'")
        override = self._validate_command(options['command']) if 'command' in options else None
        self._step_bad_contacts.clear()
        self._reward_raw = {}
        _, info = super().reset(seed=seed)
        if override is not None:
            self._command = override
        elif self._command_ranges is not None:
            self._command = self.np_random.uniform(self._command_ranges[:, 0], self._command_ranges[:, 1])
        else:
            self._command = self._configured_command.copy()
        info['command'] = self.command.tolist()
        return self._get_obs(), info

    def _unwanted_contact_bodies(self):
        bodies = set()
        for contact in self.data.contact:
            a, b = int(contact.geom1), int(contact.geom2)
            if contact.dist > 0 or self._ground_geom not in (a, b):
                continue
            other = b if a == self._ground_geom else a
            if other not in self._foot_geoms:
                bodies.add(int(self.model.geom_bodyid[other]))
        return bodies

    def _check_termination(self):
        contacts = self._unwanted_contact_bodies()
        self._step_bad_contacts.update(contacts)
        up = self.data.xmat[self._base_id].reshape(3, 3)[2, 2]
        return bool(self.data.qpos[2] <= self.termination_height
                    or up <= self._tilt_cosine+1e-12 or self._base_id in contacts)

    def _compute_reward(self, applied, previous_action, terminated):
        self._step_bad_contacts.update(self._unwanted_contact_bodies())
        terms, self._reward_raw = compute_reward_terms(self.reward_config,
            linear_velocity=self.get_base_linear_velocity(),
            angular_velocity=self.get_base_angular_velocity(), gravity=self.get_gravity_vector(),
            command=self._command, torques=self.data.actuator_force[self._actuator_ids],
            action=applied, previous_action=previous_action,
            collision_count=len(self._step_bad_contacts), terminated=terminated, dt=self.dt)
        return terms

    def step(self, action):
        self._step_bad_contacts.clear()
        obs, reward, terminated, truncated, info = super().step(action)
        info.update(command=self.command.tolist(), reward_raw=dict(self._reward_raw),
                    unwanted_contact_bodies=[self.model.body(i).name for i in sorted(self._step_bad_contacts)])
        return obs, reward, terminated, truncated, info
