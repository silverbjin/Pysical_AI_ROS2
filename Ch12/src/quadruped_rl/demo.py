"""Run random torque or a PD standing baseline; neither is a learned policy."""
import argparse
import json
import math
from pathlib import Path
import time

import numpy as np

from .env import QuadrupedEnv


def stand_action(env):
    """Joint PD torques normalized to the same limits used by the RL action."""
    kp = np.tile([40.0, 100.0, 100.0], 4)
    kd = np.tile([2.0, 4.0, 4.0], 4)
    torque = (kp * (env.nominal_joint_positions - env.data.qpos[env._qpos_ids])
              - kd * env.data.qvel[env._qvel_ids])
    return np.clip(torque / env.torque_limits, -1, 1).astype(np.float32)


def run_demo(*, steps=1000, policy="random", seed=42,
             observation_mode="textbook", target_velocity=.5, render=False):
    if isinstance(steps, bool) or not isinstance(steps, int) or steps <= 0:
        raise ValueError("steps must be a positive integer")
    if policy not in ("random", "stand"):
        raise ValueError("policy must be random or stand")
    rng = np.random.default_rng(seed)
    returns = []
    episode_return = 0.0
    reward_total = 0.0
    falls = timeouts = 0
    min_height = math.inf
    max_tilt = 0.0
    start = time.perf_counter()
    with QuadrupedEnv(observation_mode=observation_mode,
                      target_velocity=target_velocity,
                      render_mode="human" if render else None) as env:
        env.reset(seed=seed)
        for _ in range(steps):
            tick = time.perf_counter()
            action = (stand_action(env) if policy == "stand"
                      else rng.uniform(-1, 1, 12).astype(np.float32))
            obs, reward, terminated, truncated, info = env.step(action)
            episode_return += reward
            reward_total += reward
            min_height = min(min_height, info["height"])
            up = env.data.xmat[env._base_id].reshape(3, 3)[2, 2]
            max_tilt = max(max_tilt, math.degrees(math.acos(float(np.clip(up, -1, 1)))))
            if terminated or truncated:
                falls += int(terminated)
                timeouts += int(truncated)
                returns.append(episode_return)
                episode_return = 0.0
                env.reset()
            if render:
                time.sleep(max(0, env.dt - (time.perf_counter()-tick)))
        return {"policy": policy, "seed": seed, "steps": steps,
                "observation_size": int(obs.size), "target_velocity": target_velocity,
                "physics_seconds": steps * env.dt,
                "wall_seconds": time.perf_counter()-start,
                "episodes_finished": len(returns), "falls": falls, "timeouts": timeouts,
                "episode_returns": returns, "partial_episode_return": episode_return,
                "reward_total": reward_total, "height_min": min_height,
                "tilt_max_deg": max_tilt}


def positive_int(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise argparse.ArgumentTypeError("must be finite")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=positive_int, default=1000)
    parser.add_argument("--policy", choices=["random", "stand"], default="random")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--observation-mode", choices=["textbook", "full"], default="textbook")
    parser.add_argument("--target-velocity", type=finite_float, default=.5)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run_demo(steps=args.steps, policy=args.policy, seed=args.seed,
                      observation_mode=args.observation_mode,
                      target_velocity=args.target_velocity, render=args.render)
    text = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
