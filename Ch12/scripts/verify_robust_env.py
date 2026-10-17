"""Save actual perturbation traces, real PPO updates and policy reload evidence."""
import argparse
import json
from pathlib import Path

import mujoco
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.vec_env import DummyVecEnv,SubprocVecEnv

from quadruped_rl.robust_env import RobustQuadrupedEnv


def run(output):
    output.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(1)
    traces = []
    with RobustQuadrupedEnv(randomize_dynamics=False,sensor_noise=False,push_probability=0) as env:
        reset,_ = env.reset(seed=37)
        for step,value in enumerate([.1,0.,0.,0.,0.]):
            obs,_,_,_,info = env.step(np.full(12,value))
            traces.append(dict(step=step+1,commanded=value,delayed=info['delayed_action'][0],
                observed_previous_action=float(obs[36]),policy_frame_is_reset=bool(np.array_equal(obs,reset))))
        assert [t['delayed'] for t in traces] == [0.,0.,.1,0.,0.]
        assert traces[0]['policy_frame_is_reset'] and traces[1]['policy_frame_is_reset']
        assert traces[4]['observed_previous_action'] == np.float32(.1)
    domains = []
    with RobustQuadrupedEnv(push_probability=1) as env:
        for seed in [31,32,31]:
            _,info = env.reset(seed=seed)
            domains.append(info['domain_randomization'])
            _,_,_,_,push = env.step(np.zeros(12))
            assert np.any(push['external_force_world'])
            assert not np.any(env.unwrapped.data.xfrc_applied)
        assert domains[0] == domains[2]
    runs = []
    reset_contracts = []
    for task,backend in [('locomotion','dummy'),('goal','dummy'),('avoidance','subproc')]:
        reset_config = dict(task=task,sensor_noise=False,action_delay=0,
                            observation_delay=0,push_probability=0)
        with RobustQuadrupedEnv(randomize_dynamics=False,**reset_config) as baseline, \
             RobustQuadrupedEnv(randomize_dynamics=True,**reset_config) as randomized:
            plain,_ = baseline.reset(seed=4)
            changed,_ = randomized.reset(seed=4)
            a,b = baseline.unwrapped,randomized.unwrapped
            for field in ['qpos','qvel','ctrl','mocap_pos','mocap_quat']:
                np.testing.assert_array_equal(getattr(a.data,field),getattr(b.data,field))
            np.testing.assert_array_equal(plain,changed)
            assert b.data.qpos[2] == .5
            assert not np.array_equal(a.model.body_mass,b.model.body_mass)
            reset_contracts.append(dict(task=task,seed=4,height=float(b.data.qpos[2]),
                joint_positions=b.data.qpos[b._qpos_ids].tolist(),
                seeded_pose_velocity_controls_mocap_and_observation='PASS',
                mass_randomization='PASS'))
        factory = lambda: RobustQuadrupedEnv(task=task,max_episode_steps=32)
        with factory() as checker:
            check_env(checker,warn=True)
        vec = DummyVecEnv([factory,factory]) if backend=='dummy' else SubprocVecEnv([factory,factory],start_method='spawn')
        try:
            model = PPO('MlpPolicy',vec,n_steps=16,batch_size=32,n_epochs=2,
                        policy_kwargs=dict(net_arch=[32,32]),seed=19,device='cpu')
            before = [p.detach().clone() for p in model.policy.parameters()]
            model.learn(128)
            change = sum(float(torch.sum(torch.abs(a-b))) for a,b in zip(before,model.policy.parameters()))
            assert change > 0
            path = output/f'{task}_{backend}_smoke.zip'
            model.save(path)
            loaded = PPO.load(path,device='cpu')
            obs = vec.reset()
            action,_ = loaded.predict(obs,deterministic=True)
            assert np.isfinite(vec.step(action)[1]).all()
            runs.append(dict(task=task,backend=backend,transitions=128,parameter_l1_change=change,
                             checkpoint=path.name,save_reload_inference='PASS'))
        finally:
            vec.close()
    report = dict(status='PASS',mujoco=mujoco.__version__,torch=torch.__version__,
        action_observation_impulse_trace=traces,episode_domains=domains,ppo_runs=runs,
        reset_state_contracts=reset_contracts,
        limitation='Smoke updates validate integration; no learned walking, robustness improvement or hardware sim-to-real performance is established.')
    (output/'robust.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output),indent=2))


if __name__ == '__main__':
    main()
