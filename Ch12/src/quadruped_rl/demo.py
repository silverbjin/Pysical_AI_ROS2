"""Run random torque or a PD standing baseline; neither is a learned policy."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

from .env import QuadrupedEnv
from .training_env import QuadrupedTrainingEnv


def stand_action(env):
    """Joint PD torques normalized to the same limits used by the RL action."""
    if env.control_mode == "position":
        return np.zeros(12, dtype=np.float32)
    kp = np.tile([40.0, 100.0, 100.0], 4)
    # Targets in position mode are tracked at physics rate. The external torque
    # baseline is sampled at control rate; its 50 Hz derivative gain must be lower.
    kd = np.tile([2.0, 4.0, 4.0] if env.dt < .02 else [2.0, 2.0, 2.0], 4)
    torque = (kp * (env.nominal_joint_positions - env.data.qpos[env._qpos_ids])
              - kd * env.data.qvel[env._qvel_ids])
    return np.clip(torque / env.torque_limits, -1, 1).astype(np.float32)


def run_demo(*, steps=1000, policy="random", seed=42,
             observation_mode=None, target_velocity=.5, render=False,
             section="12.1", control_mode=None):
    if isinstance(steps, bool) or not isinstance(steps, int) or steps <= 0:
        raise ValueError("steps must be a positive integer")
    if policy not in ("random", "stand"):
        raise ValueError("policy must be random or stand")
    if section not in ("12.1", "12.2"):
        raise ValueError("section must be 12.1 or 12.2")
    rng = np.random.default_rng(seed)
    returns = []
    episode_return = 0.0
    reward_total = 0.0
    falls = timeouts = 0
    min_height = math.inf
    max_tilt = 0.0
    max_force = 0.0
    start = time.perf_counter()
    env_class = QuadrupedTrainingEnv if section == "12.2" else QuadrupedEnv
    settings = {}
    if observation_mode is not None:
        settings["observation_mode"] = observation_mode
    if control_mode is not None:
        settings["control_mode"] = control_mode
    with env_class(target_velocity=target_velocity,
                   render_mode="human" if render else None, **settings) as env:
        env.reset(seed=seed)
        for _ in range(steps):
            tick = time.perf_counter()
            action = (stand_action(env) if policy == "stand"
                      else rng.uniform(-1, 1, 12).astype(np.float32))
            obs, reward, terminated, truncated, info = env.step(action)
            episode_return += reward
            max_force = max(max_force, float(np.max(np.abs(env.data.actuator_force))))
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
                "section": section, "control_mode": env.control_mode,
                "frame_skip": env.frame_skip, "control_dt": env.dt,
                "observation_size": int(obs.size), "target_velocity": target_velocity,
                "physics_seconds": steps * env.dt,
                "wall_seconds": time.perf_counter()-start,
                "episodes_finished": len(returns), "falls": falls, "timeouts": timeouts,
                "episode_returns": returns, "partial_episode_return": episode_return,
                "reward_total": reward_total, "height_min": min_height,
                "tilt_max_deg": max_tilt, "actuator_force_max": max_force}


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
    parser.add_argument("--section", choices=["12.1", "12.2"], default="12.1")
    parser.add_argument("--control-mode", choices=["torque", "position"])
    parser.add_argument("--observation-mode", choices=["textbook", "full", "quaternion"])
    parser.add_argument("--target-velocity", type=finite_float, default=.5)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = run_demo(steps=args.steps, policy=args.policy, seed=args.seed,
                          observation_mode=args.observation_mode,
                          target_velocity=args.target_velocity, render=args.render,
                          section=args.section, control_mode=args.control_mode)
    except KeyboardInterrupt:
        print("Simulation closed.", file=sys.stderr)
        return 130
    text = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
