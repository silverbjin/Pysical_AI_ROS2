"""Measure vector-environment startup and steady stepping, with real MuJoCo."""
import argparse
import json
from pathlib import Path
import platform
import time

import numpy as np
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from quadruped_rl.robust_env import RobustQuadrupedEnv


def benchmark(backend, n_envs, steps=200, warmup=20, robust=True, task='locomotion'):
    factories = [lambda: RobustQuadrupedEnv(task=task, enabled=robust,max_episode_steps=1000)
                 for _ in range(n_envs)]
    started = time.perf_counter()
    vec = (DummyVecEnv(factories) if backend=='dummy' else
           SubprocVecEnv(factories,start_method='spawn'))
    try:
        vec.seed(123)
        vec.reset()
        startup = time.perf_counter()-started
        actions = np.zeros((n_envs,12),dtype=np.float32)
        for _ in range(warmup):
            vec.step(actions)
        started = time.perf_counter()
        for _ in range(steps):
            vec.step(actions)
        elapsed = time.perf_counter()-started
        return dict(backend=backend,n_envs=n_envs,task=task,robust=robust,
                    startup_reset_seconds=startup,steady_step_seconds=elapsed,
                    vector_steps=steps,transitions=steps*n_envs,
                    transitions_per_second=steps*n_envs/elapsed,
                    seconds_per_vector_step=elapsed/steps,warmup_steps=warmup)
    finally:
        vec.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--envs',type=int,nargs='+',default=[1,2,4])
    parser.add_argument('--steps',type=int,default=200)
    parser.add_argument('--warmup',type=int,default=20)
    parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--task',choices=['locomotion','goal','avoidance'],default='locomotion')
    args = parser.parse_args()
    if min(args.envs)<=0 or args.steps<=0 or args.warmup<0:
        parser.error('envs and steps must be positive; warmup nonnegative')
    results = [benchmark(backend,n,args.steps,args.warmup,not args.baseline,args.task)
               for n in args.envs for backend in ['dummy','subproc']]
    report = dict(platform=platform.platform(),python=platform.python_version(),
                  results=results,measurement='Startup includes worker creation, model loading and reset; steady steps include autoresets.',
                  limitation='CPU MuJoCo only. Throughput is hardware/task dependent; subprocess speedup is not guaranteed. No GPU simulation claim.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
