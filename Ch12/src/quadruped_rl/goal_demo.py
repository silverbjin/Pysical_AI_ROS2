"""Finite random/standing goal demo; these baselines do not navigate."""
import argparse
import json
import time

import numpy as np

from .goal_env import QuadrupedGoalEnv


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--policy',choices=['random','stand'],default='random')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--frame-path')
    parser.add_argument('--trajectory-path')
    parser.add_argument('--target',nargs=2,type=float)
    parser.add_argument('--radius-range',nargs=2,type=float,default=[2,3])
    parser.add_argument('--goal-mode',choices=['resample','terminate'],default='resample')
    args = parser.parse_args(argv)
    if args.steps <= 0 or (args.render and args.frame_path):
        parser.error('steps must be positive; choose render or frame-path')
    try:
        env = QuadrupedGoalEnv(radius_range=args.radius_range,goal_mode=args.goal_mode,
            render_mode='human' if args.render else 'rgb_array' if args.frame_path else None)
    except ValueError as error:
        parser.error(str(error))
    rng = np.random.default_rng(args.seed)
    rows = []
    falls = timeouts = arrivals = episode = 0
    total = 0.
    try:
        env.reset(seed=args.seed,options={'target':args.target} if args.target is not None else None)
        for index in range(args.steps):
            start = time.monotonic()
            action = np.zeros(12) if args.policy == 'stand' else rng.uniform(-1,1,12)
            obs,reward,done,cut,info = env.step(action)
            total += reward
            arrivals += int(info['is_success'])
            falls += int(done and not info['is_success'])
            timeouts += int(cut)
            rows.append([index,episode,env.data.time,*env.data.qpos[:3],reward,
                info['distance'],int(info['is_success']),*info['evaluated_target'][:2]])
            if args.render:
                if not env._viewer.is_running():
                    break
                time.sleep(max(0,env.dt-(time.monotonic()-start)))
            if (done or cut) and index+1 < args.steps:
                episode += 1
                env.reset()
        if args.frame_path:
            from PIL import Image
            Image.fromarray(env.render()).save(args.frame_path)
        if args.trajectory_path:
            np.savetxt(args.trajectory_path,rows,delimiter=',',header=
                'step,episode,sim_time,x,y,z,reward,distance,success,target_x,target_y',comments='')
        print(json.dumps(dict(policy=args.policy,steps=len(rows),falls=falls,timeouts=timeouts,
            arrivals=arrivals,reward_total=total,observation_size=len(obs),
            note='baseline physics demo; no trained navigation policy'),indent=2))
    except ValueError as error:
        parser.error(str(error))
    except KeyboardInterrupt:
        return 130
    finally:
        env.close()
    return 0
