"""8.7: 추론 평가 — 성공률, 종단 거리, 행동 변화량을 구분한다."""
import argparse
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO
from rl_env import ReachEnv


def terminal_distance(obs, info):
    # 6DoF ReachEnv observation = qpos[6], qvel[6], ee[3], target[3].
    if "distance" in info:
        distance = float(info["distance"])
    else:
        if np.asarray(obs).shape != (18,):
            raise ValueError("Cannot infer distance: expected ReachEnv 18D observation")
        distance = float(np.linalg.norm(obs[-6:-3] - obs[-3:]))
    if not np.isfinite(distance) or distance < 0:
        raise ValueError("Invalid terminal distance")
    return distance


def evaluate_policy_robotics(model, env, n_eval_episodes=100, seed=42, max_steps=500):
    if n_eval_episodes < 1 or max_steps < 1:
        raise ValueError("n_eval_episodes and max_steps must be positive")
    successes, returns, lengths, changes, errors = 0, [], [], [], []
    for episode in range(n_eval_episodes):
        obs, _ = env.reset(seed=seed + episode)
        prev_action, diff_sum, episode_reward = None, 0.0, 0.0
        for step in range(1, max_steps + 1):
            action, _ = model.predict(obs, deterministic=True)
            action = np.asarray(action, dtype=float)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += float(reward)
            if prev_action is not None:
                diff_sum += float(np.linalg.norm(action - prev_action))
            prev_action = action.copy()
            if terminated or truncated:
                break
        success = bool(info.get("is_success", False))
        successes += int(success)
        errors.append(terminal_distance(obs, info))
        returns.append(episode_reward)
        lengths.append(step)
        changes.append(diff_sum / max(1, step - 1))
    success_rate = 100.0 * successes / n_eval_episodes
    mean_return = float(np.mean(returns))
    print(f"Episodes={n_eval_episodes}, success={success_rate:.1f}%")
    print(f"Terminal distance (ALL episodes): {np.mean(errors)*1000:.1f} mm")
    print(f"Mean episode length: {np.mean(lengths):.1f} steps")
    print(f"Mean |delta action|/step: {np.mean(changes):.5f} (NOT physical jerk or power)")
    print(f"Mean reward: {mean_return:.3f} ± {np.std(returns):.3f}")
    return success_rate, mean_return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True, help="explicit *.zip policy path")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error(f"Policy not found: {args.model}")
    env = ReachEnv(render_mode=None)
    try:
        model = PPO.load(str(args.model), env=None, device="cpu")
        if model.observation_space != env.observation_space or model.action_space != env.action_space:
            raise ValueError("Policy/environment observation or action contract mismatch")
        evaluate_policy_robotics(model, env, args.episodes, args.seed)
    finally:
        env.close()


if __name__ == "__main__":
    main()
