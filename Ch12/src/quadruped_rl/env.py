"""Torque or position control with named joints and real MuJoCo physics."""
from importlib.resources import as_file, files
import math
from numbers import Integral
import time

import gymnasium as gym
import mujoco
import numpy as np


class QuadrupedEnv(gym.Env):
    """30/45-dimensional RPY or 31-dimensional quaternion observations."""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 100}
    joint_names = tuple(f"{leg}_{joint}_joint" for leg in ("fr", "fl", "rr", "rl")
                        for joint in ("hip", "thigh", "calf"))
    model_files = {'position': 'quadruped_position.xml', 'torque': 'quadruped.xml'}

    def __init__(self, observation_mode="textbook", render_mode=None,
                 max_episode_steps=1000, frame_skip=5, target_velocity=0.5,
                 control_mode="torque", initial_height=.41, termination_height=.14):
        super().__init__()
        if observation_mode not in ("textbook", "full", "quaternion"):
            raise ValueError("observation_mode must be textbook, full or quaternion")
        if control_mode not in ("torque", "position"):
            raise ValueError("control_mode must be torque or position")
        if render_mode not in (None, *self.metadata["render_modes"]):
            raise ValueError("Unsupported render_mode")
        for name, value in (("frame_skip", frame_skip),
                            ("max_episode_steps", max_episode_steps)):
            if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not np.isfinite(target_velocity):
            raise ValueError("target_velocity must be finite")
        if not (np.isfinite(initial_height) and np.isfinite(termination_height)
                and initial_height > termination_height > 0):
            raise ValueError("initial_height must exceed a positive termination_height")
        self.observation_mode = observation_mode
        self.control_mode = control_mode
        self.initial_height = float(initial_height)
        self.termination_height = float(termination_height)
        self.render_mode = render_mode
        self.frame_skip = int(frame_skip)
        self.max_episode_steps = int(max_episode_steps)
        self.target_velocity = float(target_velocity)
        model_name = self.model_files[control_mode]
        # Loading by resource path preserves sibling MJCF include resolution.
        with as_file(files("quadruped_rl").joinpath("models", model_name)) as path:
            self.model = mujoco.MjModel.from_xml_path(str(path))
        self.data = mujoco.MjData(self.model)
        joints = [self.model.joint(name) for name in self.joint_names]
        self._qpos_ids = np.array([j.qposadr[0] for j in joints])
        self._qvel_ids = np.array([j.dofadr[0] for j in joints])
        self._actuator_ids = np.array([self.model.actuator(name.removesuffix("_joint")
                                                        + "_motor").id
                                       for name in self.joint_names])
        self.torque_limits = np.tile([20.0, 30.0, 30.0], 4)
        self.nominal_joint_positions = np.tile([0.0, -0.5, 1.0], 4)
        self.position_action_scale = np.full(12, .35)
        self._joint_limits = self.model.jnt_range[[j.id for j in joints]].copy()
        self._base_id = self.model.body("base_link").id
        self._base_geom = self.model.geom("base_collision").id
        self._ground_geom = self.model.geom("ground").id
        self.dt = float(self.model.opt.timestep * self.frame_skip)
        self.metadata = dict(self.metadata, render_fps=round(1 / self.dt))
        self.observation_space = gym.spaces.Box(-np.inf, np.inf,
            shape=({"textbook": 30, "full": 45, "quaternion": 31}[observation_mode],),
            dtype=np.float32)
        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(12,), dtype=np.float32)
        self._previous_action = np.zeros(12)
        self._steps = 0
        self._needs_reset = True
        self._viewer = None
        self._renderer = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:3] = [0, 0, self.initial_height]
        self.data.qpos[3:7] = [1, 0, 0, 0]
        self.data.qpos[self._qpos_ids] = (self.nominal_joint_positions
                                        + self.np_random.uniform(-.01, .01, 12))
        self.data.qvel[self._qvel_ids] = self.np_random.uniform(-.01, .01, 12)
        if self.control_mode == "position":
            self.data.ctrl[self._actuator_ids] = self.nominal_joint_positions
        self._previous_action.fill(0)
        self._steps = 0
        self._needs_reset = False
        mujoco.mj_forward(self.model, self.data)
        if self.render_mode == "human":
            self.render()
        return self._get_obs(), {"observation_mode": self.observation_mode,
                                 "control_mode": self.control_mode}

    def _get_obs(self):
        # Free-joint qvel: world linear velocity, body-local angular velocity.
        w, x, y, z = self.data.qpos[3:7]
        rpy = [math.atan2(2*(w*x+y*z), 1-2*(x*x+y*y)),
               math.asin(float(np.clip(2*(w*y-z*x), -1, 1))),
               math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))]
        orientation = self.data.qpos[3:7] if self.observation_mode == "quaternion" else rpy
        components = [orientation, self.data.qvel[3:6], self.data.qpos[self._qpos_ids],
                      self.data.qvel[self._qvel_ids]]
        if self.observation_mode == "full":
            components.extend([self.data.qvel[:3], self._previous_action])
        return np.concatenate(components).astype(np.float32)

    def _check_termination(self):
        upright = self.data.xmat[self._base_id].reshape(3, 3)[2, 2]
        base_contact = any(
            {int(c.geom1), int(c.geom2)} == {self._base_geom, self._ground_geom}
            for c in self.data.contact)
        return bool(self.data.qpos[2] < self.termination_height or upright < .5 or base_contact)

    def _scale_action(self, applied):
        """Convert already validated/clipped action to N m or target radians."""
        if self.control_mode == "torque":
            return applied * self.torque_limits
        return np.clip(self.nominal_joint_positions + applied*self.position_action_scale,
                       self._joint_limits[:, 0], self._joint_limits[:, 1])

    def _ensure_finite_state(self):
        if not (np.isfinite(self.data.qpos).all() and np.isfinite(self.data.qvel).all()):
            self._needs_reset = True
            raise FloatingPointError("Non-finite MuJoCo state; reset the environment")

    def _compute_reward(self, applied, previous_action, terminated):
        """Weighted contributions; subclasses can replace the task without a new step loop."""
        torque = self.data.actuator_force[self._actuator_ids]
        return {
            "survival": 0.0 if terminated else 1.0,
            "velocity": math.exp(-((self.data.qvel[0]-self.target_velocity)/.5)**2),
            "energy": -0.002 * float(np.mean(np.abs(torque*self.data.qvel[self._qvel_ids]))),
            "action_rate": -0.01 * float(np.mean((applied-previous_action)**2)),
            "fall": -5.0 if terminated else 0.0,
        }

    def step(self, action):
        if self._needs_reset:
            raise RuntimeError("Call reset() before step() and after episode end")
        action = np.asarray(action, dtype=np.float64)
        if action.shape != (12,) or not np.isfinite(action).all():
            raise ValueError("action must contain 12 finite numbers with shape (12,)")
        self._ensure_finite_state()
        applied = np.clip(action, -1, 1)
        self.data.ctrl[self._actuator_ids] = self._scale_action(applied)
        warning_ids = (mujoco.mjtWarning.mjWARN_BADQPOS, mujoco.mjtWarning.mjWARN_BADQVEL,
                       mujoco.mjtWarning.mjWARN_BADQACC)
        before = [self.data.warning[i].number for i in warning_ids]
        # Latch falls across substeps: ground bounce must not erase a fall.
        terminated = self._check_termination()
        for _ in range(self.frame_skip):
            mujoco.mj_step(self.model, self.data)
            self._ensure_finite_state()
            if any(self.data.warning[i].number > n for i, n in zip(warning_ids, before)):
                self._needs_reset = True
                raise FloatingPointError("MuJoCo reported numerical instability; reset required")
            fallen_now = self._check_termination()
            terminated = terminated or fallen_now
        # Synchronize derived poses/contacts with the integrated qpos.
        mujoco.mj_forward(self.model, self.data)
        self._ensure_finite_state()
        self._steps += 1
        fallen_now = self._check_termination()
        terminated = terminated or fallen_now
        truncated = self._steps >= self.max_episode_steps
        try:
            terms = self._compute_reward(applied, self._previous_action, terminated)
        except FloatingPointError:
            self._needs_reset = True
            raise
        self._previous_action[:] = applied
        self._needs_reset = terminated or truncated
        info = {"reward_terms": terms, "action_clipped": bool(np.any(action != applied)),
                "control_mode": self.control_mode,
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
            # MuJoCo 3.3.7 close() requests exit but does not join its daemon
            # render thread. is_running() also only checks the exit request.
            # Its internal weakref expires after render_loop/destroy complete;
            # waiting prevents Python's GLFW atexit hook racing that cleanup.
            # Keep this version-specific compatibility use isolated here.
            sim_reference = self._viewer._sim
            deadline = time.monotonic()+5.
            while sim_reference() is not None:
                if time.monotonic() >= deadline:
                    raise RuntimeError('MuJoCo viewer did not finish shutdown within 5 seconds')
                time.sleep(.005)
            self._viewer = None
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
