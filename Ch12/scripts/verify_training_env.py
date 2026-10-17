#!/usr/bin/env python3
"""Validate section 12.2 with real position/torque dynamics and optional graphics."""
import argparse
import json
from pathlib import Path
import platform

import gymnasium
from gymnasium.utils.env_checker import check_env
import mujoco
import numpy as np

from quadruped_rl import QuadrupedTrainingEnv
from quadruped_rl.demo import run_demo, stand_action


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--human", action="store_true")
    args = parser.parse_args()
    for mode in ("position", "torque"):
        with QuadrupedTrainingEnv(control_mode=mode) as env:
            check_env(env, skip_render_check=True)
    runs = [run_demo(section="12.2", control_mode=control, policy=policy,
                     target_velocity=0, seed=seed, steps=1000)
            for control in ("position", "torque") for policy in ("random", "stand")
            for seed in (0, 42, 123)]
    checks = {"gymnasium_contract": True,
              "all_finite": all(np.isfinite(r["reward_total"]) for r in runs),
              "all_31d_50hz": all(r["observation_size"] == 31 and r["control_dt"] == .02
                                 for r in runs),
              "standing_no_falls": all(r["falls"] == 0 for r in runs if r["policy"] == "stand"),
              "episodes_end": all(r["episodes_finished"] > 0 for r in runs),
              "force_limits": all(r["actuator_force_max"] <= 30.000001 for r in runs)}
    if args.image:
        from PIL import Image
        with QuadrupedTrainingEnv(render_mode="rgb_array") as env:
            env.reset(seed=42)
            for _ in range(100):
                _, _, terminated, truncated, _ = env.step(stand_action(env))
                if terminated or truncated:
                    raise RuntimeError("Standing baseline ended during render validation")
            pixels = env.render()
            checks["rgb_render"] = bool(pixels.shape == (480, 640, 3) and pixels.std() > 5)
            args.image.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(pixels).save(args.image)
    if args.human:
        run_demo(section="12.2", policy="stand", target_velocity=0, steps=100, render=True)
        checks["human_loop_completed"] = True
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
              "versions": {"python": platform.python_version(), "mujoco": mujoco.__version__,
                           "gymnasium": gymnasium.__version__, "numpy": np.__version__},
              "runs": runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
