"""Real LiDAR/obstacle physics and PPO integration; no proficiency claim."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

from quadruped_rl import QuadrupedAvoidanceEnv
from quadruped_rl.ppo import train,play


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    destination = args.output
    (destination/'result.json').unlink(missing_ok=True)
    runs = []
    for rays in (16,32):
        for noise in (0.,.05):
            for policy in ('stand','random'):
                for seed in (0,42,123):
                    rng = np.random.default_rng(seed)
                    with QuadrupedAvoidanceEnv(num_rays=rays,lidar_noise_std=noise) as env:
                        obs,info = env.reset(seed=seed)
                        total = 0.
                        falls = collisions = arrivals = 0
                        minimum = 5.
                        for _ in range(500):
                            action = np.zeros(12) if policy=='stand' else rng.uniform(-1,1,12)
                            obs,reward,done,cut,info = env.step(action)
                            assert env.observation_space.contains(obs) and np.isfinite(reward)
                            assert reward==sum(info['reward_terms'].values())
                            assert np.array_equal(obs[48:],env._get_lidar_obs())
                            assert env.target_is_clear(env.target_pos)
                            assert np.abs(env.data.actuator_force).max()<=30.000001
                            total += reward
                            minimum = min(minimum,info['lidar_min'])
                            collisions += int(info['obstacle_collision'])
                            falls += int(info['fallen'])
                            arrivals += int(info['is_success'])
                            if done or cut:
                                env.reset()
                        assert policy!='stand' or falls==collisions==0
                        runs.append(dict(rays=rays,noise_m=noise,policy=policy,seed=seed,
                            steps=500,reward_total=total,falls=falls,collisions=collisions,
                            arrivals=arrivals,lidar_min=minimum))
    with QuadrupedAvoidanceEnv(render_mode='rgb_array',obstacle_count=3) as env:
        env.reset(seed=42,options={'target':[2,1],'obstacles':[[1.5,-1],[-1.5,-1],[0,2.5]]})
        for _ in range(100):
            env.step(np.zeros(12))
        Image.fromarray(env.render()).save(destination/'frame.png')
    training = []
    for backend,rays,steps in (('dummy',16,2048),('subproc',32,128)):
        path = destination/'ppo_runs'/backend
        result = train(path,task='avoidance',env_kwargs={'num_rays':rays},n_envs=2,backend=backend,
            total_timesteps=steps,n_steps=128 if backend=='dummy' else 32,batch_size=64,
            n_epochs=2,eval_every=512 if backend=='dummy' else 64,eval_episodes=2,
            checkpoint_every=512 if backend=='dummy' else 64,max_episode_steps=200)
        assert result['parameter_delta']>0
        replay = play(path,steps=200,expected_task='avoidance',
            trajectory_path=path/'path.csv',frame_path=path/'frame.png')
        accumulator = EventAccumulator(str(next((path/'tensorboard').rglob('events.out.tfevents.*')))).Reload()
        tags = accumulator.Tags()['scalars']
        assert {'train/value_loss','train/entropy_loss','eval/success_rate'}<=set(tags)
        training.append(dict(training=result,replay=replay,tensorboard_scalar_tags=tags))
    report = dict(status='PASS',physics_steps=12000,physics_runs=runs,
        training_transitions=2176,training=training,
        limitation='Standing/random and smoke PPO only; learned avoidance proficiency unproven')
    (destination/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',physics_steps=12000,training_transitions=2176)))


if __name__=='__main__':
    main()
