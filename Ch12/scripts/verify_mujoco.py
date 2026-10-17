#!/usr/bin/env python3
"""Exercise the installed package with real physics and optional real rendering."""
import argparse
import json
from pathlib import Path
import platform

import gymnasium
from gymnasium.utils.env_checker import check_env
import mujoco
import numpy as np

from quadruped_rl import QuadrupedEnv
from quadruped_rl.demo import run_demo, stand_action


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", type=Path)
    args = parser.parse_args()
    for mode in ("textbook", "full"):
        with QuadrupedEnv(observation_mode=mode) as env:
            check_env(env, skip_render_check=True)
    runs = [run_demo(steps=1000, policy=policy, seed=seed, observation_mode=mode,
                     target_velocity=0)
            for mode in ("textbook", "full")
            for policy in ("random", "stand") for seed in (0, 42, 123)]
    checks = {"gymnasium_contract": True,
              "all_runs_finite": all(np.isfinite(r["reward_total"]) for r in runs),
              "standing_no_falls": all(r["falls"] == 0 for r in runs if r["policy"] == "stand"),
              "random_episodes_end": all(r["falls"] > 0 for r in runs if r["policy"] == "random")}
    if args.image:
        from PIL import Image
        with QuadrupedEnv(render_mode="rgb_array") as env:
            env.reset(seed=42)
            for _ in range(100):
                _, _, terminated, truncated, _ = env.step(stand_action(env))
                if terminated or truncated:
                    raise RuntimeError("Standing episode ended before image capture")
            pixels = env.render()
            checks["rgb_render"] = bool(pixels.shape == (480, 640, 3) and pixels.std() > 5)
            args.image.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(pixels).save(args.image)
    result = {"status": "PASS" if all(checks.values()) else "FAIL",
              "checks": checks, "versions": {"python": platform.python_version(),
              "mujoco": mujoco.__version__, "gymnasium": gymnasium.__version__,
              "numpy": np.__version__}, "runs": runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
