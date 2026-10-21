"""Integration contracts: all tests use the real MuJoCo engine."""
import numpy as np
import pytest
import mujoco
from gymnasium.utils.env_checker import check_env

from quadruped_rl import QuadrupedEnv


@pytest.mark.parametrize('mode,size', [('textbook', 30), ('full', 45)])
def test_gym_contract_and_seed_replay(mode, size):
    with QuadrupedEnv(observation_mode=mode) as env:
        check_env(env, skip_render_check=True)
        first, _ = env.reset(seed=42)
        assert first.shape == (size,)
        assert first.dtype == np.float32
        action = np.linspace(-.1, .1, 12, dtype=np.float32)
        outcome = env.step(action)
        assert env.data.time == pytest.approx(.01)
        env.reset(seed=42)
        replay = env.step(action)
        np.testing.assert_array_equal(outcome[0], replay[0])
        assert outcome[1:] == replay[1:]


def test_joint_mapping_and_clipped_torques():
    with QuadrupedEnv(observation_mode='full') as env:
        env.reset(seed=3)
        obs, _, _, _, info = env.step(np.full(12, 2.0))
        np.testing.assert_array_equal(obs[33:45], np.ones(12))
        np.testing.assert_allclose(env.data.ctrl, [20, 30, 30] * 4)
        assert info['action_clipped'] is True
        for index, name in enumerate(env.joint_names):
            joint = env.model.joint(name)
            assert env.model.actuator_trnid[index, 0] == joint.id
            assert obs[6 + index] == pytest.approx(env.data.qpos[joint.qposadr[0]])


@pytest.mark.parametrize('action', [np.zeros(11), np.zeros((12, 1)),
                                   np.full(12, np.nan), np.full(12, np.inf)])
def test_bad_action_is_rejected_before_physics_changes(action):
    with QuadrupedEnv() as env:
        env.reset(seed=0)
        before = env.data.qpos.copy()
        with pytest.raises(ValueError):
            env.step(action)
        assert env.data.time == 0
        np.testing.assert_array_equal(env.data.qpos, before)


def test_timeout_differs_from_fall_and_reset_clears_previous_action():
    with QuadrupedEnv(max_episode_steps=1, observation_mode='full') as env:
        env.reset(seed=1)
        _, _, terminated, truncated, _ = env.step(np.zeros(12))
        assert not terminated and truncated
        with pytest.raises(RuntimeError):
            env.step(np.zeros(12))
        obs, _ = env.reset(seed=1)
        np.testing.assert_array_equal(obs[33:], np.zeros(12))
        env.data.qpos[2] = .05
        mujoco.mj_forward(env.model, env.data)
        _, reward, terminated, _, info = env.step(np.zeros(12))
        assert terminated
        assert info['reward_terms']['survival'] == 0
        assert info['reward_terms']['fall'] == -5
        assert reward == pytest.approx(sum(info['reward_terms'].values()))


def test_full_observation_world_velocity_and_body_angular_velocity():
    with QuadrupedEnv(observation_mode='full') as env:
        env.reset(seed=0)
        env.data.qpos[3:7] = [np.sqrt(.5), 0, 0, np.sqrt(.5)]
        env.data.qvel[:6] = [1, 2, 3, .1, .2, .3]
        mujoco.mj_forward(env.model, env.data)
        obs = env._get_obs()
        np.testing.assert_allclose(obs[:3], [0, 0, np.pi/2], atol=1e-6)
        np.testing.assert_allclose(obs[3:6], [.1, .2, .3], atol=1e-6)
        np.testing.assert_allclose(obs[30:33], [1, 2, 3], atol=1e-6)


def test_step_requires_reset():
    with QuadrupedEnv() as env:
        with pytest.raises(RuntimeError):
            env.step(np.zeros(12))


@pytest.mark.parametrize('kwargs', [dict(frame_skip=0), dict(frame_skip=1.5),
    dict(max_episode_steps=0), dict(target_velocity=np.nan),
    dict(observation_mode='unknown'), dict(render_mode='unknown')])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        QuadrupedEnv(**kwargs)
