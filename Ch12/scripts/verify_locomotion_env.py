#!/usr/bin/env python3
"""Exercise real command-conditioned physics and inspect reward accounting."""
import argparse
import json
from pathlib import Path
import platform

import gymnasium
from gymnasium.utils.env_checker import check_env
import mujoco
import numpy as np

from quadruped_rl import QuadrupedLocomotionEnv
from quadruped_rl.demo import run_demo, stand_action


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--image', type=Path)
    args = parser.parse_args()
    with QuadrupedLocomotionEnv() as env:
        check_env(env, skip_render_check=True)
    commands = [(0, 0, 0), (.5, .2, .3)]
    runs = [run_demo(section='12.3', control_mode=control, policy=policy,
                     command=command, seed=seed, steps=1000)
            for control in ('position', 'torque') for policy in ('random', 'stand')
            for command in commands for seed in (0, 42, 123)]
    checks = {
        'gymnasium_contract': True,
        '48d_50hz': all(r['observation_size'] == 48 and r['control_dt'] == .02 for r in runs),
        'all_finite': all(np.isfinite(r['reward_total']) for r in runs),
        'standing_no_falls': all(r['falls'] == 0 for r in runs if r['policy'] == 'stand'),
        'force_limits': all(r['actuator_force_max'] <= 30.000001 for r in runs),
        'reward_accounting': all(np.isclose(r['reward_total'], sum(r['reward_term_totals'].values()))
                                 for r in runs),
        'episodes_end': all(r['episodes_finished'] > 0 for r in runs),
    }
    pairs = []
    for control in ('position', 'torque'):
        for seed in (0, 42, 123):
            pair = [r for r in runs if r['control_mode'] == control
                    and r['policy'] == 'stand' and r['seed'] == seed]
            pairs.append(pair[0]['reward_term_totals']['linear_tracking'] >
                         pair[1]['reward_term_totals']['linear_tracking'])
    checks['standing_command_changes_tracking_reward'] = all(pairs)
    if args.image:
        from PIL import Image
        with QuadrupedLocomotionEnv(command=(0, 0, 0), render_mode='rgb_array') as env:
            env.reset(seed=42)
            for _ in range(100):
                _, _, ended, truncated, _ = env.step(stand_action(env))
                if ended or truncated:
                    raise RuntimeError('Standing ended before image capture')
            pixels = env.render()
            checks['rgb_render'] = bool(pixels.shape == (480, 640, 3) and pixels.std() > 5)
            args.image.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(pixels).save(args.image)
    report = dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks,
                  versions=dict(python=platform.python_version(), mujoco=mujoco.__version__,
                                gymnasium=gymnasium.__version__, numpy=np.__version__), runs=runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
