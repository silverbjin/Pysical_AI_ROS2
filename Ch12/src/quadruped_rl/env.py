"""A small torque-controlled Gymnasium environment using real MuJoCo physics."""
from importlib.resources import files
import math
from numbers import Integral

import gymnasium as gym
import mujoco
import numpy as np


class QuadrupedEnv(gym.Env):
    """Textbook observation (30) or extended observation (45); see the lab guide."""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 100}
    joint_names = tuple(f"{leg}_{joint}_joint" for leg in ("fr", "fl", "rr", "rl")
                        for joint in ("hip", "thigh", "calf"))

    def __init__(self, observation_mode="textbook", render_mode=None,
                 max_episode_steps=1000, frame_skip=5, target_velocity=0.5):
        super().__init__()
        if observation_mode not in ("textbook", "full"):
            raise ValueError("observation_mode must be textbook or full")
        if render_mode not in (None, *self.metadata["render_modes"]):
            raise ValueError("Unsupported render_mode")
        for name, value in (("frame_skip", frame_skip),
                            ("max_episode_steps", max_episode_steps)):
            if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not np.isfinite(target_velocity):
            raise ValueError("target_velocity must be finite")
        self.observation_mode = observation_mode
        self.render_mode = render_mode
        self.frame_skip = int(frame_skip)
        self.max_episode_steps = int(max_episode_steps)
        self.target_velocity = float(target_velocity)
        model_text = files("quadruped_rl").joinpath("models/quadruped.xml").read_text()
        self.model = mujoco.MjModel.from_xml_string(model_text)
        self.data = mujoco.MjData(self.model)
        joints = [self.model.joint(name) for name in self.joint_names]
        self._qpos_ids = np.array([j.qposadr[0] for j in joints])
        self._qvel_ids = np.array([j.dofadr[0] for j in joints])
        self._actuator_ids = np.array([self.model.actuator(name.removesuffix("_joint")
                                                        + "_motor").id
                                       for name in self.joint_names])
        self.torque_limits = np.tile([20.0, 30.0, 30.0], 4)
        self.nominal_joint_positions = np.tile([0.0, -0.5, 1.0], 4)
        self._base_id = self.model.body("base_link").id
        self._base_geom = self.model.geom("base_collision").id
        self._ground_geom = self.model.geom("ground").id
        self.dt = float(self.model.opt.timestep * self.frame_skip)
        self.metadata = dict(self.metadata, render_fps=round(1 / self.dt))
        self.observation_space = gym.spaces.Box(-np.inf, np.inf,
            shape=(30 if observation_mode == "textbook" else 45,), dtype=np.float32)
        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(12,), dtype=np.float32)
        self._previous_action = np.zeros(12)
        self._steps = 0
        self._needs_reset = True
        self._viewer = None
        self._renderer = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:3] = [0, 0, .41]
        self.data.qpos[3:7] = [1, 0, 0, 0]
        self.data.qpos[self._qpos_ids] = (self.nominal_joint_positions
                                        + self.np_random.uniform(-.01, .01, 12))
        self.data.qvel[self._qvel_ids] = self.np_random.uniform(-.01, .01, 12)
        self._previous_action.fill(0)
        self._steps = 0
        self._needs_reset = False
        mujoco.mj_forward(self.model, self.data)
        if self.render_mode == "human":
            self.render()
        return self._get_obs(), {"observation_mode": self.observation_mode}

    def _get_obs(self):
        # Free-joint qvel: world linear velocity, body-local angular velocity.
        w, x, y, z = self.data.qpos[3:7]
        rpy = [math.atan2(2*(w*x+y*z), 1-2*(x*x+y*y)),
               math.asin(float(np.clip(2*(w*y-z*x), -1, 1))),
               math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))]
        components = [rpy, self.data.qvel[3:6], self.data.qpos[self._qpos_ids],
                      self.data.qvel[self._qvel_ids]]
        if self.observation_mode == "full":
            components.extend([self.data.qvel[:3], self._previous_action])
        return np.concatenate(components).astype(np.float32)

    def _check_termination(self):
        upright = self.data.xmat[self._base_id].reshape(3, 3)[2, 2]
        base_contact = any(
            {int(c.geom1), int(c.geom2)} == {self._base_geom, self._ground_geom}
            for c in self.data.contact)
        return bool(self.data.qpos[2] < .14 or upright < .5 or base_contact)

    def step(self, action):
        if self._needs_reset:
            raise RuntimeError("Call reset() before step() and after episode end")
        action = np.asarray(action, dtype=np.float64)
        if action.shape != (12,) or not np.isfinite(action).all():
            raise ValueError("action must contain 12 finite numbers with shape (12,)")
        applied = np.clip(action, -1, 1)
        torque = applied * self.torque_limits
        self.data.ctrl[self._actuator_ids] = torque
        for _ in range(self.frame_skip):
            mujoco.mj_step(self.model, self.data)
        # Synchronize derived poses/contacts with the integrated qpos.
        mujoco.mj_forward(self.model, self.data)
        if not (np.isfinite(self.data.qpos).all() and np.isfinite(self.data.qvel).all()):
            self._needs_reset = True
            raise FloatingPointError("Non-finite MuJoCo state; reset the environment")
        self._steps += 1
        terminated = self._check_termination()
        truncated = self._steps >= self.max_episode_steps
        terms = {
            "survival": 0.0 if terminated else 1.0,
            "velocity": math.exp(-((self.data.qvel[0]-self.target_velocity)/.5)**2),
            "energy": -0.002 * float(np.mean(np.abs(torque*self.data.qvel[self._qvel_ids]))),
            "action_rate": -0.01 * float(np.mean((applied-self._previous_action)**2)),
            "fall": -5.0 if terminated else 0.0,
        }
        self._previous_action[:] = applied
        self._needs_reset = terminated or truncated
        info = {"reward_terms": terms, "action_clipped": bool(np.any(action != applied)),
                "height": float(self.data.qpos[2]), "sim_time": float(self.data.time)}
        if self.render_mode == "human":
            self.render()
        return self._get_obs(), float(sum(terms.values())), terminated, truncated, info

    def render(self):
        if self.render_mode == "rgb_array":
            if self._renderer is None:
                self._renderer = mujoco.Renderer(self.model, height=480, width=640)
            self._renderer.update_scene(self.data, camera="overview")
            return self._renderer.render()
        if self.render_mode == "human":
            if self._viewer is None:
                from mujoco import viewer
                self._viewer = viewer.launch_passive(self.model, self.data)
            if self._viewer.is_running():
                self._viewer.sync()
        return None

    def close(self):
        if self._viewer is not None:
            self._viewer.close()
            self._viewer = None
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
