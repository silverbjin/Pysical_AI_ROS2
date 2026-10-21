"""8.7: 실제 rgb_array 이미지 기반 정책 평가 녹화."""
import argparse
from pathlib import Path

from gymnasium.wrappers import RecordVideo
from stable_baselines3 import PPO
from evaluate_robot import evaluate_policy_robotics
from recording_env import ReachRGBEnv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--video-dir", type=Path, default=Path("videos/evaluation"))
    args = parser.parse_args()
    if not args.model.is_file() or args.episodes < 1:
        parser.error("Provide an existing policy zip and positive episodes")
    env = RecordVideo(
        ReachRGBEnv(),
        video_folder=str(args.video_dir),
        episode_trigger=lambda ep: ep < args.episodes,
        disable_logger=True
    )
    try:
        model = PPO.load(str(args.model), env=None, device="cpu")
        if model.observation_space != env.observation_space or model.action_space != env.action_space:
            raise ValueError("Policy/environment contract mismatch")
        evaluate_policy_robotics(model, env, args.episodes, args.seed)
    finally:
        env.close()


if __name__ == "__main__":
    main()
