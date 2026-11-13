#!/usr/bin/env python3
"""Ch08 §8.7: bounded deterministic PPO policy evaluation with true distances.

No claim of policy quality from a short smoke training run. This evaluates
the exact supplied ZIP, reports actual success/timeout, and NEVER reports
missing final distance as a 0mm "perfect" steady-state error.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import torch
from stable_baselines3 import PPO
from rl_env import ReachEnv


def _hash(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def evaluate_policy_robotics(model, env, n_eval_episodes=10,
                              max_steps=300, seed=1000):
    """Return explicit per-episode measurements; never infer missing distance."""
    if n_eval_episodes < 1 or max_steps < 1:
        raise ValueError("episodes/steps must be positive")
    if (tuple(model.observation_space.shape)!=(18,)
            or tuple(model.action_space.shape)!=(6,)):
        raise RuntimeError(
            f"CH08_87_MODEL_SHAPE_MISMATCH expected=18/6 "
            f"observed={model.observation_space.shape}/{model.action_space.shape}"
        )

    episodes = []
    for i in range(n_eval_episodes):
        observation, _ = env.reset(seed=seed+i)
        rewards = 0.0
        changes = []
        previous_action = None
        success = False
        reason = "STEP_LIMIT"
        last_distance = None
        for step in range(max_steps):
            action, _ = model.predict(observation, deterministic=True)
            action = np.asarray(action, dtype=np.float32)
            if action.shape != (6,) or not np.isfinite(action).all():
                raise RuntimeError("CH08_87_POLICY_ACTION_INVALID")
            if previous_action is not None:
                changes.append(float(np.linalg.norm(action-previous_action)))
            previous_action=action.copy()
            observation, reward, terminated, truncated, info = env.step(action)
            rewards+=float(reward)
            if observation.shape != (18,) or not np.isfinite(observation).all():
                raise RuntimeError("CH08_87_INVALID_STEP_OBSERVATION")
            distance=float(info.get("distance", float("nan")))
            # Independently measure real EE-target geometry rather than trust
            # a default 0.0 or an unrelated reward component.
            geometry=float(np.linalg.norm(observation[12:15]-observation[15:18]))
            if not (math.isfinite(distance) and math.isfinite(geometry)
                    and abs(distance-geometry)<1e-4):
                raise RuntimeError(
                    f"CH08_87_DISTANCE_MISSING_OR_INCONSISTENT distance={distance} geometry={geometry}"
                )
            last_distance=distance
            if not math.isfinite(rewards):
                raise RuntimeError("CH08_87_REWARD_NONFINITE")
            if bool(terminated) or bool(truncated):
                success=bool(info["is_success"]) and distance<0.05
                reason="SUCCESS" if success else ("TRUNCATED" if truncated else "TERMINATED")
                break
        if last_distance is None:
            raise RuntimeError("CH08_87_NO_STEP_DISTANCE")
        episodes.append({
            "episode":i, "seed":seed+i, "steps":step+1,
            "reason":reason, "success":success,
            "final_distance_m":last_distance,
            "episode_return":rewards,
            "mean_action_delta":float(np.mean(changes)) if changes else 0.0,
        })

    success_count=sum(e["success"] for e in episodes)
    mean_return=float(np.mean([e["episode_return"] for e in episodes]))
    final_distances=[e["final_distance_m"] for e in episodes]
    metrics={
        "episode_count":len(episodes),
        "success_count":success_count,
        "success_rate_pct":100.0*success_count/len(episodes),
        "mean_return":mean_return,
        "mean_final_distance_m":float(np.mean(final_distances)),
        "std_final_distance_m":float(np.std(final_distances)),
        "mean_episode_steps":float(np.mean([e["steps"] for e in episodes])),
        "mean_action_delta":float(np.mean([e["mean_action_delta"] for e in episodes])),
        "seed_start":seed, "max_steps":max_steps,
        "individual_episodes":episodes,
    }
    print(
        f"CH08_87_ACTUAL_POLICY_EVALUATION_PASS episodes={len(episodes)} "
        f"success_count={success_count} "
        f"mean_final_distance_m={metrics['mean_final_distance_m']:.6f} "
        f"success_rate_pct={metrics['success_rate_pct']:.1f}",
        flush=True,
    )
    return metrics


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",type=Path,default=Path("models/ppo_reach_final.zip"))
    p.add_argument("--episodes",type=int,default=10)
    p.add_argument("--max-steps",type=int,default=300)
    p.add_argument("--seed",type=int,default=1000)
    p.add_argument("--output-json",type=Path,default=None)
    args=p.parse_args()
    torch.set_num_threads(2)
    model_file=args.model.resolve()
    if not model_file.is_file():
        raise FileNotFoundError(f"CH08_87_MODEL_MISSING {model_file}")
    env=ReachEnv(render_mode=None)
    try:
        model=PPO.load(str(model_file),device="cpu")
        if model.observation_space.shape!=(18,) or model.action_space.shape!=(6,):
            raise RuntimeError("CH08_87_SAVED_MODEL_NOT_COMPATIBLE_WITH_6DOF")
        metrics=evaluate_policy_robotics(
            model,env,n_eval_episodes=args.episodes,
            max_steps=args.max_steps,seed=args.seed,
        )
        result={
            "chapter":"Ch08","section":"8.7","status":"SCOPED_PASS",
            "scope":"deterministic_existing_policy_true_distance_metrics",
            "model_zip_sha256":_hash(model_file),
            "source_sha":os.environ.get("RUN_SOURCE_SHA","LOCAL_UNPINNED"),
            "metrics":metrics,
            "training_history_claim":"NOT_RUN",
            "real_robot":"NOT_RUN","rgb_video":"NOT_RUN",
            "ch10":"HOLD",
        }
        if args.output_json:
            path=args.output_json.resolve()
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                raise FileExistsError("CH08_87_REFUSING_OVERWRITE_RECEIPT")
            tmp=path.with_suffix(".tmp")
            with tmp.open("w",encoding="utf-8") as f:
                json.dump(result,f,ensure_ascii=False,sort_keys=True,indent=2)
                f.write("\n");f.flush();os.fsync(f.fileno())
            os.replace(tmp,path)
        print("CH08_87_REAL_EE_DISTANCE_AND_BOUNDED_METRICS_SCOPED_PASS",flush=True)
        return 0
    finally:
        env.close()


if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"CH08_87_FAIL type={type(exc).__name__} reason={exc}",file=sys.stderr,flush=True)
        sys.exit(1)
