#!/usr/bin/env python3
"""Ch08 #168: genuine frozen PPO MuJoCo EE→target velocity, no training.

Only new missing kinematic vector data. Original 10x300 PPO performance eval,
prior 3x120 action/reward traces and test-only PD goals are NOT rerun.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import torch
from stable_baselines3 import PPO

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "Ch08/ros2_ws"
sys.path.insert(0, str(WS))
from rl_env import ReachEnv

OUT = ROOT / "ci-results/ch08-168-vector"
OUT.mkdir(parents=True, exist_ok=True)
MODEL = WS / "models/ppo_reach_final.zip"
XML = WS / "src/my_robot_description/assets/simple_arm_6dof.xml"
ENV = WS / "rl_env.py"
SEEDS = (1000, 1001)
HORIZON = 120


def sha256(path):
    d = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            d.update(b)
    return d.hexdigest()


def trace_seed(model, seed):
    env = ReachEnv(render_mode=None)
    try:
        obs, _ = env.reset(seed=seed)
        assert obs.shape == (18,) and env.model.nu == 6
        goal = np.array(obs[15:18], dtype=np.float64).copy()
        previous_ee = np.array(obs[12:15], dtype=np.float64).copy()
        previous_distance = float(np.linalg.norm(goal - previous_ee))
        previous_time = float(env.data.time)
        initial_distance = previous_distance
        steps = []
        for i in range(HORIZON):
            action, _ = model.predict(obs, deterministic=True)
            action = np.asarray(action, dtype=np.float64)
            if action.shape != (6,) or not np.isfinite(action).all() or np.max(np.abs(action)) > 1.00001:
                raise RuntimeError("CH08_168_INVALID_FROZEN_ACTION")
            next_obs, reward, terminated, truncated, info = env.step(action.astype(np.float32))
            timestamp = float(env.data.time)
            dt = timestamp - previous_time
            if not 0 < dt < 0.1:
                raise RuntimeError(f"CH08_168_BAD_MUJOCO_DT {dt}")
            ee = np.array(next_obs[12:15], dtype=np.float64).copy()
            target = np.array(next_obs[15:18], dtype=np.float64).copy()
            if not np.allclose(target, goal, atol=1e-5) or not np.isfinite(ee).all():
                raise RuntimeError("CH08_168_TARGET_MOVED_OR_EE_NONFINITE")
            distance = float(np.linalg.norm(target - ee))
            if not math.isfinite(distance) or abs(distance - float(info["distance"])) > 1e-4:
                raise RuntimeError("CH08_168_TRUE_DISTANCE_NOT_MATCHED")
            velocity = (ee - previous_ee) / dt
            unit_to_goal = (goal - previous_ee) / max(previous_distance, 1e-12)
            projected_approach_speed = float(np.dot(velocity, unit_to_goal))
            radial_distance_rate = (distance - previous_distance) / dt
            if not all(math.isfinite(x) for x in
                       (projected_approach_speed, radial_distance_rate, float(reward))):
                raise RuntimeError("CH08_168_NONFINITE_PROJECTION")
            steps.append({
                "step": i + 1, "sim_time_sec": timestamp, "dt_sec": dt,
                "ee_prev_xyz_m": previous_ee.tolist(), "ee_xyz_m": ee.tolist(),
                "target_xyz_m": target.tolist(), "actual_action": action.tolist(),
                "distance_prev_m": previous_distance, "distance_m": distance,
                "ee_velocity_xyz_m_s": velocity.tolist(),
                "projected_approach_speed_m_s": projected_approach_speed,
                "distance_derivative_m_s": radial_distance_rate,
            })
            previous_ee, previous_distance, previous_time = ee, distance, timestamp
            obs = next_obs
            if terminated or truncated:
                break
        if not steps:
            raise RuntimeError("CH08_168_EMPTY_REAL_TRACE")
        k = min(range(len(steps)), key=lambda i: steps[i]["distance_m"])
        before = steps[:k+1]
        after = steps[k+1:]
        summary = {
            "seed": seed, "actual_steps": len(steps),
            "initial_distance_m": initial_distance,
            "closest_approach_step": k + 1,
            "closest_approach_m": steps[k]["distance_m"],
            "final_distance_m": steps[-1]["distance_m"],
            "post_min_distance_increase_m": steps[-1]["distance_m"] - steps[k]["distance_m"],
            "pre_min_mean_projected_speed_m_s": float(np.mean([s["projected_approach_speed_m_s"] for s in before])),
            "post_min_mean_projected_speed_m_s": float(np.mean([s["projected_approach_speed_m_s"] for s in after])) if after else None,
            "post_min_receding_step_fraction": float(np.mean([s["projected_approach_speed_m_s"] < 0 for s in after])) if after else None,
            "goal_radius_0p05_reached": any(s["distance_m"] < 0.05 for s in steps),
            "target_xyz_m": goal.tolist(),
        }
        file = OUT / f"vector_trace_seed_{seed}.json"
        file.write_text(json.dumps(steps, sort_keys=True, indent=2) + "\n")
        print(f"CH08_168_ACTUAL_VECTOR_PROJECTION seed={seed} closest_m={summary['closest_approach_m']:.5f} post_mean_m_s={summary['post_min_mean_projected_speed_m_s']}", flush=True)
        return summary
    finally:
        env.close()


def main():
    original = {str(p.relative_to(ROOT)): sha256(p) for p in (MODEL, XML, ENV)}
    torch.set_num_threads(2)
    model = PPO.load(str(MODEL), device="cpu")
    if tuple(model.observation_space.shape) != (18,) or tuple(model.action_space.shape) != (6,):
        raise RuntimeError("CH08_168_ORIGINAL_FROZEN_SPACE_INVALID")
    rows = [trace_seed(model, s) for s in SEEDS]
    if any(sha256(ROOT / key) != value for key, value in original.items()):
        raise RuntimeError("CH08_168_ORIGINAL_ASSET_MODIFIED")
    receipt = {
        "chapter": "Ch08", "section": "8.7", "status": "DIAGNOSTIC_SCOPED_PASS",
        "source_sha": os.environ.get("RUN_SOURCE_SHA", "UNPINNED"),
        "scope": "actual_EE_xyz_target_xyz_projected_velocity_frozen_PPO",
        "seeds": list(SEEDS), "horizon_max_steps_per_seed": HORIZON,
        "assets_sha256": original, "frozen_PPO_unchanged": True,
        "original_10x300_evaluation": "NOT_RERUN",
        "original_PPO_performance": "0_OF_10_FAILURE_PRESERVED",
        "test_only_PD_success": "NOT_RERUN",
        "training": "NOT_RUN", "real_hardware": "NOT_RUN",
        "gui": "NOT_RUN", "ch10": "HOLD", "summaries": rows,
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print("CH08_168_REAL_FROZEN_PPO_EE_VECTOR_MEASUREMENT_SCOPED_PASS", flush=True)
    print("CH08_168_ORIGINAL_PPO_PERFORMANCE_0_OF_10_FAIL_PRESERVED", flush=True)


if __name__ == "__main__":
    main()
