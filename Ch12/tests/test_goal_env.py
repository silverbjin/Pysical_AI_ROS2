import math
import os
import mujoco
import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from quadruped_rl.goal_env import QuadrupedGoalEnv


def test_goal_frames_and_angle_boundary():
    with QuadrupedGoalEnv() as env:
        env.reset(seed=42, options={'target': [0, 2]})
        env.data.qpos[3:7] = [math.cos(math.pi/4),0,0,math.sin(math.pi/4)]
        mujoco.mj_forward(env.model, env.data)
        assert np.allclose(env.goal_features(), [2,0,1], atol=1e-6)
        env.data.qpos[3:7] = [1,0,0,0]
        mujoco.mj_forward(env.model, env.data)
        env.set_target([-2,1e-8])
        a = env.goal_features()
        env.set_target([-2,-1e-8])
        b = env.goal_features()
        assert np.linalg.norm(a-b) < 1e-6
        assert env._get_obs().shape == (48,)
        assert env.observation_mode == 'goal'


def test_global_translation_and_rotation_invariance():
    with QuadrupedGoalEnv() as env:
        env.reset(seed=2,options={'target':[2,1]})
        original = env.goal_features()
        angle = 1.2
        rotation = np.array([[math.cos(angle),-math.sin(angle)],
                             [math.sin(angle),math.cos(angle)]])
        translation = np.array([5.,-3.])
        env.data.qpos[:2] = translation
        env.data.qpos[3:7] = [math.cos(angle/2),0,0,math.sin(angle/2)]
        env.set_target(rotation @ np.array([2.,1.])+translation)
        assert np.allclose(env.goal_features(),original)


def test_marker_does_not_change_robot_physics():
    from quadruped_rl import QuadrupedLocomotionEnv
    with QuadrupedLocomotionEnv() as base, QuadrupedGoalEnv() as goal:
        base.reset(seed=2)
        goal.reset(seed=2,options={'target':[0,0]})
        for _ in range(20):
            base.step(np.zeros(12))
            goal.step(np.zeros(12))
        assert np.allclose(base.data.qpos,goal.data.qpos,atol=1e-12)
        assert np.allclose(base.data.qvel,goal.data.qvel,atol=1e-12)


def test_trail_expiry_and_target_update_no_reward_spike():
    with QuadrupedGoalEnv(trail_seconds=.05) as env:
        env.reset(seed=2)
        env.set_target([50,0])
        _,_,_,_,info = env.step(np.zeros(12))
        assert abs(info['reward_terms']['progress']) < .01
        for _ in range(5):
            env.step(np.zeros(12))
        assert all(env.data.time-t <= .05+1e-12 for t,_ in env.trajectory)


def test_seed_radius_and_marker_collision():
    with QuadrupedGoalEnv() as env:
        a, _ = env.reset(seed=7)
        target = env.target_pos
        b, _ = env.reset(seed=7)
        assert np.array_equal(a,b)
        assert 2 <= np.linalg.norm(target[:2]) <= 3
        assert np.array_equal(env.data.mocap_pos[env._target_mocap_id],target)
        geom = env.model.geom('target_marker').id
        assert env.model.geom_contype[geom] == env.model.geom_conaffinity[geom] == 0
        target[:] = 100
        assert not np.array_equal(target,env.target_pos)


def test_arrival_atomic_resample_and_progress():
    with QuadrupedGoalEnv() as env:
        env.reset(seed=4, options={'target':[.1,0]})
        obs, reward, done, cut, info = env.step(np.zeros(12))
        assert info['is_success'] and info['goals_reached'] == 1
        assert info['reward_terms']['arrival'] == 10
        assert not done and not cut
        assert np.allclose(obs[9:12],env.goal_features())
        assert env._prev_dist == pytest.approx(env.goal_features()[0])
        assert info['evaluated_target'] != info['target']
        _, _, _, _, next_info = env.step(np.zeros(12))
        assert not next_info['is_success']
        assert abs(next_info['reward_terms']['progress']) < .1
        assert reward == pytest.approx(sum(info['reward_terms'].values()))


def test_arrival_termination_and_fallen_gate():
    with QuadrupedGoalEnv(goal_mode='terminate') as env:
        env.reset(seed=4, options={'target':[0,0]})
        _, _, done, _, info = env.step(np.zeros(12))
        assert done and info['is_success']
        with pytest.raises(RuntimeError):
            env.step(np.zeros(12))
        env.reset(seed=4, options={'target':[0,0]})
        env.data.qpos[2] = .1
        mujoco.mj_forward(env.model, env.data)
        _, _, done, _, info = env.step(np.zeros(12))
        assert done and not info['is_success']
        assert info['reward_terms']['arrival'] == info['reward_terms']['progress'] == 0


def test_path_bounded_reset_and_checker():
    with QuadrupedGoalEnv(trail_capacity=5) as env:
        check_env(env, skip_render_check=True)
        env.reset(seed=3)
        for _ in range(10):
            env.step(np.zeros(12))
        assert len(env.trajectory) == 5
        env.reset(seed=3)
        assert len(env.trajectory) == 1


@pytest.mark.parametrize('kwargs', [dict(radius_range=[3,2]),dict(radius_range=[-1,2]),
    dict(arrival_radius=0),dict(goal_mode='oops'),dict(trail_capacity=0)])
def test_invalid_goal_config(kwargs):
    with pytest.raises(ValueError):
        QuadrupedGoalEnv(**kwargs)


@pytest.mark.skipif(os.environ.get('CH12_TEST_RENDER') != '1',reason='Enable real GL rendering')
def test_goal_marker_visible_in_rgb_and_camera_follows_goal():
    with QuadrupedGoalEnv(render_mode='rgb_array') as env:
        env.reset(seed=42,options={'target':[2,1]})
        for target in ([2,1],[-3,-2]):
            env.set_target(target)
            frame = env.render()
            red = (frame[:,:,0].astype(int)>frame[:,:,1].astype(int)+50)
            assert red.sum() > 30


def test_heading_quaternion_requires_finite_nonzero_wxyz_and_is_scale_invariant():
    q = [math.cos(math.pi/4), 0, 0, math.sin(math.pi/4)]
    assert QuadrupedGoalEnv.quat_to_yaw(q) == pytest.approx(math.pi/2)
    assert QuadrupedGoalEnv.quat_to_yaw(np.array(q)*3) == pytest.approx(math.pi/2)
    for bad in ([0, 0, 0, 0], [np.nan, 0, 0, 1], [1, 0, 0]):
        with pytest.raises(ValueError, match='quaternion'):
            QuadrupedGoalEnv.quat_to_yaw(bad)
