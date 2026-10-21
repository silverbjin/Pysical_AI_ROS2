"""PPO training and portable, task-checked inference bundles (section 12.4)."""
import argparse
from dataclasses import asdict
from functools import partial
import importlib.metadata
import json
import math
from numbers import Integral
from pathlib import Path
import time

import numpy as np

from .locomotion_env import QuadrupedLocomotionEnv
from .rewards import RewardConfig


SCHEMAS = {'locomotion': 'locomotion-v1-48', 'goal': 'goal-polar-sincos-v1-48',
           'avoidance':'avoidance-goal-body-lidar-v1','robust':'robust-task-sensor-delay-v1'}


def make_env(task, env_kwargs, monitor_path=None):
    from stable_baselines3.common.monitor import Monitor
    kwargs = dict(env_kwargs)
    if 'reward_config' in kwargs:
        kwargs['reward_config'] = RewardConfig(**kwargs['reward_config'])
    if task == 'locomotion':
        env = QuadrupedLocomotionEnv(**kwargs)
    elif task == 'goal':
        from .goal_env import QuadrupedGoalEnv
        env = QuadrupedGoalEnv(**kwargs)
    elif task == 'avoidance':
        from .avoidance_env import QuadrupedAvoidanceEnv
        env = QuadrupedAvoidanceEnv(**kwargs)
    elif task == 'robust':
        from .robust_env import RobustQuadrupedEnv
        env = RobustQuadrupedEnv(**kwargs)
    else:
        raise ValueError('Unknown task')
    return Monitor(env, filename=monitor_path,
        info_keywords=('obstacle_collision','lidar_min') if task=='avoidance' else ())


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def train(output, *, task='locomotion', env_kwargs=None, total_timesteps=2_000_000,
          n_envs=8, backend='dummy', device='cpu', seed=42, n_steps=2048,
          batch_size=256, n_epochs=10, learning_rate=3e-4, gamma=.99,
          ent_coef=.005, eval_every=10000, eval_episodes=5,
          checkpoint_every=100000, max_episode_steps=1000, verbose=0):
    """Create a new run directory. Counts are total environment transitions.

    PPO rounds the requested transition count up to a full rollout. Raw inputs
    are used without VecNormalize; the manifest completely specifies the env.
    """
    for name, value in dict(total_timesteps=total_timesteps,n_envs=n_envs,n_steps=n_steps,
            batch_size=batch_size,n_epochs=n_epochs,eval_every=eval_every,
            eval_episodes=eval_episodes,checkpoint_every=checkpoint_every,
            max_episode_steps=max_episode_steps).items():
        if isinstance(value,bool) or not isinstance(value,Integral) or value <= 0:
            raise ValueError(f'{name} must be a positive integer')
    if n_steps < 2 or batch_size < 2 or n_steps*n_envs % batch_size:
        raise ValueError('batch_size must divide n_steps*n_envs; n_steps/batch_size >= 2')
    if task not in SCHEMAS or backend not in ('dummy','subproc'):
        raise ValueError('Unknown task or backend')
    if device not in ('cpu','cuda','auto'):
        raise ValueError('device must be cpu, cuda or auto')
    if (not math.isfinite(learning_rate) or learning_rate <= 0
            or not math.isfinite(gamma) or not 0 < gamma <= 1
            or not math.isfinite(ent_coef) or ent_coef < 0):
        raise ValueError('Invalid learning rate, gamma or entropy coefficient')
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
    from stable_baselines3.common.evaluation import evaluate_policy
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
    if device == 'cuda' and not torch.cuda.is_available():
        raise ValueError('CUDA requested but unavailable; use --device cpu')
    # Small MLPs are often faster with one CPU thread; record this choice.
    torch.set_num_threads(1)
    kwargs = dict(env_kwargs or {})
    kwargs['max_episode_steps'] = max_episode_steps
    if kwargs.get('render_mode') is not None:
        raise ValueError('Training environments must not render')
    if isinstance(kwargs.get('reward_config'),RewardConfig):
        kwargs['reward_config'] = asdict(kwargs['reward_config'])
    try:
        kwargs = json.loads(json.dumps(kwargs,allow_nan=False))
    except (ValueError,TypeError) as error:
        raise ValueError('env_kwargs must be a finite JSON object') from error
    # Validate the real environment before creating output or worker processes.
    probe = make_env(task,kwargs)
    observation_size = probe.observation_space.shape[0]
    probe.close()
    root = Path(output).resolve()
    root.mkdir(parents=True,exist_ok=False)
    for directory in ('monitor','best_model','evaluation','checkpoints','tensorboard'):
        (root/directory).mkdir()
    training_env = evaluation_env = None
    model = None
    config = dict(total_timesteps=total_timesteps,n_envs=n_envs,backend=backend,
        device=device,seed=seed,n_steps=n_steps,batch_size=batch_size,n_epochs=n_epochs,
        learning_rate=learning_rate,gamma=gamma,ent_coef=ent_coef,gae_lambda=.95,
        clip_range=.2,net_arch=dict(pi=[256,256],vf=[256,256]),activation='Tanh',
        torch_threads=1,eval_every=eval_every,eval_episodes=eval_episodes,
        checkpoint_every=checkpoint_every)
    evaluation_kwargs = dict(kwargs)
    if task in ('goal','avoidance') or (task=='robust' and kwargs.get('task','locomotion') in ('goal','avoidance')):
        evaluation_kwargs['goal_mode'] = 'terminate'
    manifest = dict(format_version=1,task=task,observation_schema=SCHEMAS[task],
        env_kwargs=kwargs,observation_size=observation_size,action_size=12,normalization='none',
        evaluation_env_kwargs=evaluation_kwargs,
        training=config,eval_callback_frequency=max(eval_every//n_envs,1),
        versions={name:importlib.metadata.version(name) for name in
            ('physical-ai-quadruped-rl','stable-baselines3','torch','mujoco','gymnasium','numpy')})
    _write_json(root/'manifest.json',manifest)
    try:
        factories = [partial(make_env,task,kwargs,str(root/'monitor'/f'worker_{i}'))
                     for i in range(n_envs)]
        training_env = (SubprocVecEnv(factories,start_method='spawn') if backend == 'subproc'
                        else DummyVecEnv(factories))
        training_env.seed(seed)
        evaluation_env = make_env(task,evaluation_kwargs,str(root/'evaluation/monitor'))
        evaluation_env.reset(seed=seed+10000)
        evaluation_env.action_space.seed(seed+10000)
        evaluator = EvalCallback(evaluation_env,n_eval_episodes=eval_episodes,
            eval_freq=manifest['eval_callback_frequency'],
            best_model_save_path=str(root/'best_model'),log_path=str(root/'evaluation'),
            deterministic=True,verbose=verbose)
        checkpoint = CheckpointCallback(save_freq=max(checkpoint_every//n_envs,1),
            save_path=str(root/'checkpoints'),name_prefix='ppo_quadruped',verbose=verbose)
        model = PPO('MlpPolicy',training_env,learning_rate=learning_rate,n_steps=n_steps,
            batch_size=batch_size,n_epochs=n_epochs,gamma=gamma,gae_lambda=.95,
            clip_range=.2,ent_coef=ent_coef,policy_kwargs=dict(
                net_arch=config['net_arch'],activation_fn=torch.nn.Tanh),
            tensorboard_log=str(root/'tensorboard'),seed=seed,device=device,verbose=verbose)
        # SB3 saves extra algorithm attributes inside each ZIP, including callback
        # checkpoints. Space sizes alone cannot distinguish the two 48-D tasks.
        model.chapter12_schema = SCHEMAS[task]
        model.chapter12_env_kwargs = kwargs
        before = torch.cat([p.detach().flatten().cpu() for p in model.policy.parameters()])
        model.learn(total_timesteps=total_timesteps,callback=[evaluator,checkpoint])
        after = torch.cat([p.detach().flatten().cpu() for p in model.policy.parameters()])
        if not torch.isfinite(after).all():
            raise FloatingPointError('Non-finite PPO parameters')
        model.save(root/'final_model')
        # Always evaluate the final update, even for runs shorter than eval_every.
        successes = []
        def record_success(local_vars,global_vars):
            if local_vars['done'] and 'is_success' in local_vars['info']:
                successes.append(bool(local_vars['info']['is_success']))
        mean, std = evaluate_policy(model,evaluation_env,n_eval_episodes=eval_episodes,
                                    deterministic=True,callback=record_success)
        if not math.isfinite(mean) or not math.isfinite(std):
            raise FloatingPointError('Non-finite evaluation')
        if mean > evaluator.best_mean_reward:
            model.save(root/'best_model/best_model')
        result = dict(status='PASS',task=task,timesteps=model.num_timesteps,
            requested_timesteps=total_timesteps,parameter_delta=float(torch.linalg.vector_norm(after-before)),
            final_eval_mean=float(mean),final_eval_std=float(std),
            best_eval_mean=float(max(mean,evaluator.best_mean_reward)),output=str(root),
            final_eval_success_rate=float(np.mean(successes)) if successes else None,
            proves='training/save/load pipeline only; not trained walking proficiency')
        _write_json(root/'result.json',result)
        return result
    except KeyboardInterrupt:
        if model is not None:
            model.save(root/'interrupted_model')
        _write_json(root/'result.json',dict(status='INTERRUPTED'))
        raise
    except Exception as error:
        # Keep an explicit failure record for a run that already has a manifest.
        _write_json(root/'result.json', dict(status='FAIL',
            error_type=type(error).__name__, error=str(error)))
        raise
    finally:
        if training_env is not None:
            training_env.close()
        if evaluation_env is not None:
            evaluation_env.close()


def load_bundle(output, *, model_name='best_model/best_model.zip',render_mode=None,
                expected_task=None, device='cpu'):
    from stable_baselines3 import PPO
    root = Path(output).resolve()
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    task = manifest.get('task')
    saved_numpy=manifest.get('versions',{}).get('numpy')
    if saved_numpy and saved_numpy.split('.')[0]!=np.__version__.split('.')[0]:
        raise ValueError('NumPy major version differs from training; use the recorded environment or retrain')
    if expected_task is not None and task != expected_task:
        raise ValueError('Model task does not match requested task')
    if (manifest.get('format_version') != 1 or task not in SCHEMAS
            or manifest.get('observation_schema') != SCHEMAS[task]
            or manifest.get('normalization') != 'none'):
        raise ValueError('Unsupported model observation schema/normalization')
    kwargs = dict(manifest['env_kwargs'],render_mode=render_mode)
    env = make_env(task,kwargs)
    try:
        try:
            model = PPO.load(root/model_name,device=device)
        except ModuleNotFoundError as error:
            if 'numpy' in str(error):
                raise ValueError('Checkpoint NumPy serialization incompatible; use its training environment or retrain') from error
            raise
        if (getattr(model,'chapter12_schema',None) != SCHEMAS[task]
                or getattr(model,'chapter12_env_kwargs',None) != manifest['env_kwargs']):
            raise ValueError('Model task/schema/environment differs from manifest')
        if model.observation_space != env.observation_space or model.action_space != env.action_space:
            raise ValueError('Model spaces do not match environment')
    except BaseException:
        env.close()
        raise
    return model,env,manifest


def play(output, *, steps=1000,model_name='best_model/best_model.zip',render=False,
         seed=42,expected_task=None,trajectory_path=None,frame_path=None):
    if isinstance(steps,bool) or not isinstance(steps,Integral) or steps <= 0:
        raise ValueError('steps must be a positive integer')
    if render and frame_path:
        raise ValueError('Choose human rendering or frame output')
    model,env,manifest = load_bundle(output,model_name=model_name,
        render_mode='human' if render else 'rgb_array' if frame_path else None,
        expected_task=expected_task)
    reward_total = 0.
    episodes = successes = collisions = 0
    rows = []
    try:
        obs,_ = env.reset(seed=seed)
        for index in range(steps):
            start = time.monotonic()
            action,_ = model.predict(obs,deterministic=True)
            obs,reward,done,cut,info = env.step(action)
            reward_total += reward
            successes += int(info.get('is_success',False))
            collisions += int(info.get('obstacle_collision',False))
            target = info.get('evaluated_target',[np.nan,np.nan])
            rows.append([index,episodes,float(env.unwrapped.data.time),
                         *env.unwrapped.data.qpos[:3].tolist(),float(reward),
                         float(info.get('distance',np.nan)),int(info.get('is_success',False)),
                         *target[:2],float(info.get('lidar_min',np.nan)),
                         int(info.get('obstacle_collision',False))])
            if render:
                viewer = env.unwrapped._viewer
                if viewer is not None and not viewer.is_running():
                    break
                time.sleep(max(0,env.unwrapped.dt-(time.monotonic()-start)))
            if done or cut:
                episodes += 1
                if index+1 < steps:
                    obs,_ = env.reset()
        if frame_path:
            from PIL import Image
            Image.fromarray(env.render()).save(frame_path)
        if trajectory_path:
            np.savetxt(trajectory_path,rows,delimiter=',',header=
                'step,episode,sim_time,x,y,z,reward,distance,success,target_x,target_y,lidar_min,collision',comments='')
        return dict(task=manifest['task'],steps=len(rows),reward_total=reward_total,
                    episodes=episodes,successes=successes,collisions=collisions)
    finally:
        env.close()


def train_main(argv=None):
    parser = argparse.ArgumentParser(description='Train chapter 12 PPO (a new output directory is required)')
    parser.add_argument('--output',required=True)
    parser.add_argument('--task',choices=tuple(SCHEMAS),default='locomotion')
    for name,default in [('total-timesteps',2000000),('n-envs',8),('n-steps',2048),
            ('batch-size',256),('n-epochs',10),('eval-every',10000),('eval-episodes',5),
            ('checkpoint-every',100000),('max-episode-steps',1000),('seed',42)]:
        parser.add_argument('--'+name,type=int,default=default)
    parser.add_argument('--backend',choices=['dummy','subproc'],default='dummy')
    parser.add_argument('--device',choices=['cpu','cuda','auto'],default='cpu')
    parser.add_argument('--learning-rate',type=float,default=3e-4)
    parser.add_argument('--gamma',type=float,default=.99)
    parser.add_argument('--ent-coef',type=float,default=.005)
    parser.add_argument('--env-config',type=Path,help='JSON object of environment constructor options')
    args = vars(parser.parse_args(argv))
    path = args.pop('env_config')
    try:
        kwargs = json.loads(path.read_text(encoding='utf-8')) if path else {}
        if not isinstance(kwargs,dict):
            raise ValueError('env-config must be a JSON object')
        print(json.dumps(train(**args,env_kwargs=kwargs,verbose=1),indent=2))
    except (ValueError,FileExistsError,FileNotFoundError) as error:
        parser.error(str(error))
    except KeyboardInterrupt:
        print('Training interrupted; model saved.')
        return 130
    return 0


def play_main(argv=None):
    parser = argparse.ArgumentParser(description='Replay a saved PPO bundle')
    parser.add_argument('--output',required=True)
    parser.add_argument('--model-name',default='best_model/best_model.zip')
    parser.add_argument('--steps',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--expected-task',choices=tuple(SCHEMAS))
    parser.add_argument('--trajectory-path')
    parser.add_argument('--frame-path')
    args = vars(parser.parse_args(argv))
    try:
        print(json.dumps(play(**args),indent=2))
    except (ValueError,FileNotFoundError) as error:
        parser.error(str(error))
    except KeyboardInterrupt:
        return 130
    return 0
