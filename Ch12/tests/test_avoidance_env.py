import math
import os

import mujoco
import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from quadruped_rl.avoidance_env import QuadrupedAvoidanceEnv


def test_real_ray_distance_rotation_and_exclusions():
    with QuadrupedAvoidanceEnv(obstacle_count=1,lidar_noise_std=0) as env:
        obs,_ = env.reset(seed=42,options={'target':[-2,0],'obstacles':[[2,0]]})
        assert obs.shape == (64,) and obs.dtype == np.float32
        assert env.lidar_distances[0] == pytest.approx(1.8)
        assert obs[48] == pytest.approx(1-1.8/5)
        assert env.lidar_distances[8] == 5 # target, robot and floor excluded
        env.data.qpos[3:7] = [math.cos(math.pi/4),0,0,math.sin(math.pi/4)]
        mujoco.mj_forward(env.model,env.data)
        env.refresh_lidar()
        assert env.lidar_distances[12] == pytest.approx(1.8)
        assert env.lidar_distances[0] == 5


def test_seed_layout_no_overlap_and_target_resample():
    with QuadrupedAvoidanceEnv() as env:
        a,_ = env.reset(seed=42)
        layout = env.obstacle_positions
        b,_ = env.reset(seed=42)
        assert np.array_equal(a,b)
        assert np.array_equal(layout,env.obstacle_positions)
        for point,half in zip(layout,env.obstacle_half_sizes):
            assert env.point_box_distance([0,0],point,half) >= 1
            assert env.point_box_distance(env.target_pos,point,half) >= env.arrival_radius+.55
        for i in range(10):
            for j in range(i):
                assert np.any(np.abs(layout[i]-layout[j]) >=
                    env.obstacle_half_sizes[i,:2]+env.obstacle_half_sizes[j,:2]+.15)
        for _ in range(20):
            env.reset_target()
            assert env.target_is_clear(env.target_pos)


def test_noise_is_metres_cached_and_reproducible():
    with QuadrupedAvoidanceEnv(obstacle_count=0,lidar_noise_std=.05) as env:
        a,_ = env.reset(seed=7)
        assert np.array_equal(a,env._get_obs())
        assert np.array_equal(a,env._get_obs())
        b,_ = env.reset(seed=7)
        assert np.array_equal(a,b)
        assert np.all(env.lidar_distances == 5)
        samples = []
        for _ in range(100):
            env.refresh_lidar()
            samples.extend(env._get_lidar_obs())
        # 5cm / 5m = .01 normalized std; clipping at max halves this distribution.
        assert 0 < np.mean(samples) < .01
        assert np.max(samples) < .05
        env.reset(seed=8)
        assert not np.array_equal(a,env._get_obs())


def test_collision_terminates_without_arrival_and_requires_reset():
    with QuadrupedAvoidanceEnv(obstacle_count=1,lidar_noise_std=0) as env:
        env.reset(seed=2,options={'target':[2,0],'obstacles':[[0,2]]})
        # Move a box into the base using the real mocap/physics interface.
        env.data.mocap_pos[env._obstacle_mocap_ids[0]] = [.49,0,.5]
        mujoco.mj_forward(env.model,env.data)
        assert env._check_collision()
        contacts = [c for c in env.data.contact if c.dist<=0 and
                    ((int(c.geom1) in env._robot_geoms and int(c.geom2) in env._obstacle_ids)
                     or (int(c.geom2) in env._robot_geoms and int(c.geom1) in env._obstacle_ids))]
        assert contacts
        for contact in contacts:
            a,b = int(contact.geom1),int(contact.geom2)
            contact.geom1,contact.geom2 = b,a
        assert env._check_collision() # both actual contact operand orders accepted
        _,reward,done,_,info = env.step(np.zeros(12))
        assert done and info['obstacle_collision'] and not info['is_success']
        assert not info['fallen']
        assert reward == -100 and sum(info['reward_terms'].values()) == -100
        assert info['reward_terms']['arrival'] == 0
        with pytest.raises(RuntimeError):
            env.step(np.zeros(12))


def test_transient_contact_is_latched_across_physics_substeps():
    with QuadrupedAvoidanceEnv(obstacle_count=1,lidar_noise_std=0,frame_skip=100) as env:
        env.reset(seed=2,options={'target':[2,0],'obstacles':[[0,2]]})
        env.data.mocap_pos[env._obstacle_mocap_ids[0]] = [.7,0,.5]
        env.data.qvel[0] = 2
        mujoco.mj_forward(env.model,env.data)
        assert not env._check_collision()
        _,reward,done,_,info = env.step(np.zeros(12))
        # The robot touches and separates during this one control step.
        assert not env._check_collision()
        assert info['obstacle_collision'] and done
        assert reward == -100
        assert not info['fallen']


def test_safety_cost_uses_clean_metres_and_dt():
    with QuadrupedAvoidanceEnv(obstacle_count=1,lidar_noise_std=0) as env:
        env.reset(seed=3,options={'target':[2,0],'obstacles':[[0,2]]})
        # Ahead, surface .7m from sensor: within .8m but no robot contact.
        env.data.mocap_pos[env._obstacle_mocap_ids[0]] = [.9,0,.5]
        mujoco.mj_forward(env.model,env.data)
        _,_,done,_,info = env.step(np.zeros(12))
        assert not done
        expected = -2*np.maximum(0,.8-env.lidar_distances).mean()/.8*env.dt
        assert info['reward_terms']['safety'] == pytest.approx(expected)
        assert info['reward_terms']['safety'] < 0


def test_fixed_layout_target_rejection_and_empty_scan():
    with QuadrupedAvoidanceEnv(obstacle_count=1) as env:
        env.reset(seed=1,options={'target':[2,0],'obstacles':[[0,2]]})
        before = env.target_pos
        with pytest.raises(ValueError):
            env.set_target([0,2])
        assert np.array_equal(before,env.target_pos)
        with pytest.raises(ValueError):
            env.reset(options={'obstacles':[[0,0]]})
    with QuadrupedAvoidanceEnv(obstacle_count=0,lidar_noise_std=0) as env:
        obs,_ = env.reset(seed=1)
        assert np.all(obs[48:]==0)
        check_env(env,skip_render_check=True)


def test_32_rays_dropout_and_target_transition_consistency():
    with QuadrupedAvoidanceEnv(num_rays=32,lidar_dropout=1,obstacle_count=1) as env:
        env.reset(seed=3,options={'target':[.1,0],'obstacles':[[0,2]]})
        assert env.observation_space.shape==(80,)
        assert np.all(env._get_lidar_obs()==0)
        assert env.lidar_distances.min()<5
        obs,_,done,_,info = env.step(np.zeros(12))
        assert not done and info['is_success']
        assert env.target_is_clear(env.target_pos)
        assert np.allclose(obs[9:12],env.goal_features())
        assert np.array_equal(obs[48:],env._get_lidar_obs())
        assert env._prev_dist==env.goal_features()[0]


def test_dropout_does_not_remove_clean_safety_penalty():
    with QuadrupedAvoidanceEnv(obstacle_count=1,lidar_dropout=1,num_rays=32) as env:
        env.reset(seed=3,options={'target':[2,0],'obstacles':[[0,2]]})
        env.data.mocap_pos[env._obstacle_mocap_ids[0]] = [.9,0,.5]
        mujoco.mj_forward(env.model,env.data)
        obs,_,_,_,info = env.step(np.zeros(12))
        assert np.all(obs[48:]==0)
        assert info['reward_terms']['safety']<0


def test_demo_separates_upright_collision_from_fall(monkeypatch,capsys):
    import json
    import quadruped_rl.avoidance_env as module
    from quadruped_rl.goal_demo import main
    class ContactEnv(QuadrupedAvoidanceEnv):
        def reset(self,**kwargs):
            result = super().reset(**kwargs)
            self.data.mocap_pos[self._obstacle_mocap_ids[0]] = [.49,0,.5]
            mujoco.mj_forward(self.model,self.data)
            return result
    monkeypatch.setattr(module,'QuadrupedAvoidanceEnv',ContactEnv)
    assert main(['--task','avoidance','--policy','stand','--steps','1','--obstacle-count','1'])==0
    report = json.loads(capsys.readouterr().out)
    assert report['collisions']==1 and report['falls']==0


@pytest.mark.parametrize('kwargs',[dict(num_rays=1),dict(lidar_max_range=0),
    dict(lidar_noise_std=-1),dict(lidar_dropout=1.1),dict(obstacle_count=11),
    dict(safety_distance=6),dict(collision_penalty=-1)])
def test_invalid_settings(kwargs):
    with pytest.raises(ValueError):
        QuadrupedAvoidanceEnv(**kwargs)


@pytest.mark.skipif(os.environ.get('CH12_TEST_RENDER') != '1',reason='Real GL test')
def test_rgb_obstacles_and_lidar():
    with QuadrupedAvoidanceEnv(render_mode='rgb_array',obstacle_count=1) as env:
        env.reset(seed=42,options={'target':[2,1],'obstacles':[[1,-1]]})
        image = env.render()
        assert image.shape == (480,640,3) and image.std()>1
        scene = env._renderer.scene
        assert sum(geom.type==mujoco.mjtGeom.mjGEOM_LINE for geom in scene.geoms[:scene.ngeom])==16


def test_lidar_rejects_nonfinite_ray_before_policy_observation(monkeypatch):
    with QuadrupedAvoidanceEnv(obstacle_count=0) as env:
        env.reset(seed=4)
        monkeypatch.setattr(mujoco, 'mj_ray', lambda *args, **kwargs: float('nan'))
        with pytest.raises(FloatingPointError, match='LiDAR'):
            env.refresh_lidar()
