#!/usr/bin/env python3
"""Minimal headless physical/API test for Ch08 ReachEnv; NOT PPO performance."""
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import gymnasium
import mujoco

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "Ch08/ros2_ws"))
from rl_env import ReachEnv

out = root / "ci-results/extended/Ch08"
out.mkdir(parents=True, exist_ok=True)
result = {"scope": "Ch08 8.2-8.5 headless model and Gymnasium 5-return API",
          "status": "FAIL",
          "versions": {"mujoco": mujoco.__version__, "gymnasium": gymnasium.__version__,
                       "numpy": np.__version__}, "not_run": [
              "8.6 PPO gradient update or policy training", "8.7 TensorBoard/RGB viewer",
              "8.8 ROS/real robot controller", "goal reach rate"]}
env = ReachEnv(render_mode=None)
try:
    obs0, info0 = env.reset(seed=42)
    obs1, info1 = env.reset(seed=42)
    assert env.action_space.shape == (6,), "action shape not 6"
    assert env.observation_space.shape == (18,), "observation shape not 18"
    assert obs0.shape == (18,) and obs1.shape == (18,)
    assert np.allclose(obs0, obs1), "seed repeatability failed"
    assert np.all(np.isfinite(obs0)), "nonfinite reset observation"
    rewards = []
    for i in range(60):
        action = np.array([math.sin(i/9 + j/7) * .15 for j in range(6)],
                          dtype=np.float32)
        answer = env.step(action)
        assert isinstance(answer, tuple) and len(answer) == 5
        obs, reward, terminated, truncated, detail = answer
        assert env.observation_space.contains(obs), "observation invalid/out of shape"
        assert math.isfinite(float(reward)), "reward not finite"
        assert isinstance(terminated, bool) and isinstance(truncated, bool)
        for key in ("reward_dist", "reward_ctrl", "reward_smooth",
                    "reward_contact", "reward_bonus", "is_success"):
            assert key in detail, "missing " + key
        assert math.isclose(float(reward), float(detail["reward_total"]),
                            rel_tol=1e-5, abs_tol=1e-5)
        rewards.append(float(reward))
        if terminated or truncated:
            obs, info = env.reset(seed=42 + i)
            assert env.observation_space.contains(obs)
    result["status"] = "PASS"
    result["checks"] = {"reset_determinism": True, "model_nu": env.model.nu,
                         "action_shape": list(env.action_space.shape),
                         "observation_shape": list(env.observation_space.shape),
                         "steps": 60,
                         "finite_rewards": True,
                         "min_reward": min(rewards),
                         "max_reward": max(rewards)}
    print("CH08_MUJOCO_GYM_HEADLESS_CONTRACT_PASS " + json.dumps(result["checks"]), flush=True)
finally:
    env.close()
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
