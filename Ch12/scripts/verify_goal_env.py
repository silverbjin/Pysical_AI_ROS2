"""Real physics regression for the goal task. Does not claim learned navigation."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from quadruped_rl import QuadrupedGoalEnv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    runs = []
    for radius in ((1.,1.),(2.,3.)):
        for mode in ('terminate','resample'):
            for policy in ('stand','random'):
                for seed in (0,42,123):
                    rng = np.random.default_rng(seed)
                    with QuadrupedGoalEnv(radius_range=radius,goal_mode=mode) as env:
                        obs,_ = env.reset(seed=seed)
                        total = 0.
                        falls = arrivals = timeouts = 0
                        peak_force = 0.
                        for _ in range(1000):
                            action = np.zeros(12) if policy == 'stand' else rng.uniform(-1,1,12)
                            obs,reward,done,cut,info = env.step(action)
                            assert env.observation_space.contains(obs) and np.isfinite(obs).all()
                            assert np.isfinite(reward) and np.isclose(reward,sum(info['reward_terms'].values()))
                            assert np.allclose(obs[9:12],env.goal_features())
                            assert env._prev_dist == env.goal_features()[0]
                            peak_force = max(peak_force,float(np.abs(env.data.actuator_force).max()))
                            total += reward
                            arrivals += int(info['is_success'])
                            falls += int(done and not info['is_success'])
                            timeouts += int(cut)
                            if done or cut:
                                env.reset()
                        assert peak_force <= 30.000001
                        assert policy != 'stand' or falls == 0
                        runs.append(dict(radius=radius,mode=mode,policy=policy,seed=seed,
                            steps=1000,falls=falls,arrivals=arrivals,timeouts=timeouts,
                            reward_total=total,max_actuator_force=peak_force))
    with QuadrupedGoalEnv(render_mode='rgb_array') as env:
        env.reset(seed=42,options={'target':[2,1]})
        for _ in range(100):
            env.step(np.zeros(12))
        frame = env.render()
        assert frame.shape == (480,640,3) and frame.dtype == np.uint8 and frame.std() > 1
        Image.fromarray(frame).save(args.output/'frame.png')
        assert env._renderer.scene.ngeom >= len(env.trajectory)
    result = dict(status='PASS',runs=runs,total_control_steps=24000,
                  rgb='PASS',limitation='Standing/random baselines; no trained goal-reaching claim')
    (args.output/'mujoco.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',runs=len(runs),steps=24000)))


if __name__ == '__main__':
    main()
