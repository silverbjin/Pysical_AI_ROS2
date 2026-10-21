"""8.1: 경험 실습 — 6DoF ReachEnv의 실제 관측·행동 계약 확인."""
import argparse
import time
import numpy as np
from rl_env import ReachEnv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--max-steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--human", action="store_true", help="GUI 뷰어 사용")
    args = parser.parse_args()
    if args.episodes < 1 or args.max_steps < 1:
        parser.error("episodes와 max-steps는 양수여야 합니다")
    env = ReachEnv(render_mode="human" if args.human else None)
    try:
        for episode in range(args.episodes):
            obs, _ = env.reset(seed=args.seed + episode)
            print(f"Episode {episode + 1}: obs={obs.shape}, action={env.action_space.shape}, "
                  f"target={obs[-3:].tolist()}")
            for step in range(1, args.max_steps + 1):
                action = env.action_space.sample()
                obs, reward, terminated, truncated, info = env.step(action)
                if step % 50 == 0:
                    # 원본 ReachEnv는 info['distance']를 항상 제공하지 않음.
                    distance = float(np.linalg.norm(obs[-6:-3] - obs[-3:]))
                    print(f"  step={step}, reward={reward:.4f}, distance={distance:.4f} m")
                if args.human:
                    time.sleep(float(env.model.opt.timestep) * 5)
                if terminated or truncated:
                    break
            reason = "success" if terminated else ("environment timeout" if truncated else "external step limit")
            print(f"Episode {episode + 1}: {reason}, steps={step}")
    finally:
        env.close()


if __name__ == "__main__":
    main()
