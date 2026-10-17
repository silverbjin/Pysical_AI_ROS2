"""Literal mathematical expectations plus real MuJoCo MDP boundary checks."""
import math
from dataclasses import replace

import mujoco
import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from quadruped_rl import QuadrupedLocomotionEnv, RewardConfig
from quadruped_rl.rewards import compute_reward_terms
from quadruped_rl.demo import main


def reward_fixture(**updates):
    data = dict(linear_velocity=np.zeros(3), angular_velocity=np.zeros(3),
        gravity=np.array([0., 0., -1.]), command=np.zeros(3), torques=np.zeros(12),
        action=np.zeros(12), previous_action=np.zeros(12), collision_count=0,
        terminated=False, dt=.02)
    data.update(updates)
    return compute_reward_terms(RewardConfig(), **data)


def test_gaussian_uses_squared_error_and_yaw_tracking():
    terms, raw = reward_fixture(linear_velocity=np.array([.5, 0, 0]),
                               angular_velocity=np.array([0, 0, .5]))
    assert raw['linear_tracking'] == pytest.approx(math.exp(-1))
    assert raw['yaw_tracking'] == pytest.approx(math.exp(-1))
    assert terms['linear_tracking'] == pytest.approx(.02 * math.exp(-1))
    assert terms['yaw_tracking'] == pytest.approx(.01 * math.exp(-1))
    perfect, _ = reward_fixture()
    assert sum(perfect.values()) == pytest.approx(.04)


def test_torque_action_and_collision_costs_and_terminal_gating():
    terms, _ = reward_fixture(torques=np.full(12, 2.), action=np.ones(12), collision_count=2)
    assert terms['torque'] == pytest.approx(-.000096)
    assert terms['action_rate'] == pytest.approx(-.0024)
    assert terms['collision'] == pytest.approx(-.04)
    terminal, _ = reward_fixture(terminated=True)
    assert terminal['linear_tracking'] == terminal['yaw_tracking'] == terminal['orientation'] == 0
    assert terminal['termination'] == -10
    assert sum(terminal.values()) == -10


def test_orientation_does_not_reward_upside_down_and_rates_scale_with_dt():
    _, raw = reward_fixture(gravity=np.array([0, 0, 1.]))
    assert raw['orientation'] == pytest.approx(math.exp(-40))
    first, _ = reward_fixture()
    second, _ = reward_fixture(dt=.01)
    assert sum(first.values()) == pytest.approx(2 * sum(second.values()))


@pytest.mark.parametrize('kwargs', [dict(linear_sigma=0), dict(yaw_sigma=-1),
    dict(torque_weight=-1), dict(fall_penalty=np.nan), dict(orientation_sigma=np.inf)])
def test_bad_reward_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        RewardConfig(**kwargs)


def test_48d_body_frame_observation_and_command_yaw_invariance():
    with QuadrupedLocomotionEnv(command=(1, .2, -.3)) as env:
        env.reset(seed=0)
        env.data.qpos[3:7] = [np.sqrt(.5), 0, 0, np.sqrt(.5)]
        env.data.qvel[:6] = [1, 0, .1, .2, .3, .4]
        env.data.qpos[env._qpos_ids] = env.nominal_joint_positions
        mujoco.mj_forward(env.model, env.data)
        obs = env._get_obs()
        assert obs.shape == (48,) and obs.dtype == np.float32
        np.testing.assert_allclose(obs[:3], [0, -1, .1], atol=1e-6)
        np.testing.assert_allclose(obs[3:6], [.2, .3, .4])
        np.testing.assert_allclose(obs[6:9], [0, 0, -1], atol=1e-6)
        np.testing.assert_allclose(obs[9:12], [1, .2, -.3])
        np.testing.assert_allclose(obs[12:24], np.zeros(12))
        np.testing.assert_array_equal(obs[36:48], np.zeros(12))


def test_gravity_sign_and_45_degree_tilt_termination():
    with QuadrupedLocomotionEnv() as env:
        env.reset(seed=0)
        for angle, ended in [(44, False), (45, True), (46, True)]:
            half = math.radians(angle)/2
            env.data.qpos[3:7] = [math.cos(half), math.sin(half), 0, 0]
            mujoco.mj_forward(env.model, env.data)
            np.testing.assert_allclose(env.get_gravity_vector(),
                [0, -math.sin(2*half), -math.cos(2*half)], atol=1e-12)
            assert env._check_termination() is ended


def test_previous_applied_action_is_updated_after_reward():
    with QuadrupedLocomotionEnv(command=(0, 0, 0)) as env:
        env.reset(seed=42)
        action = np.full(12, .5)
        obs, reward, _, _, info = env.step(action)
        assert info['reward_terms']['action_rate'] == pytest.approx(-.0006)
        assert reward == pytest.approx(sum(info['reward_terms'].values()))
        np.testing.assert_array_equal(obs[36:48], action)
        obs, _, _, _, info = env.step(action)
        assert info['reward_terms']['action_rate'] == 0
        obs, _ = env.reset(seed=42)
        np.testing.assert_array_equal(obs[36:48], np.zeros(12))


def test_position_action_scale_and_actual_force_cost():
    with QuadrupedLocomotionEnv(action_scale=.5) as env:
        env.reset(seed=0)
        _, _, _, _, info = env.step(np.full(12, -2.))
        np.testing.assert_allclose(env.data.ctrl, [-.5, -1, .5] * 4)
        force_squared = np.sum(env.data.actuator_force[env._actuator_ids]**2)
        assert info['reward_terms']['torque'] == pytest.approx(-.0001 * force_squared * .02)


def test_contact_filter_ignores_feet_and_penalizes_real_calf_contact():
    with QuadrupedLocomotionEnv() as env:
        env.reset(seed=0)
        env.data.qpos[2] = .40
        mujoco.mj_forward(env.model, env.data)
        assert env._unwanted_contact_bodies() == set()
        env.data.qpos[2] = .30
        mujoco.mj_forward(env.model, env.data)
        bodies = env._unwanted_contact_bodies()
        assert bodies
        assert all('foot' not in env.model.body(i).name for i in bodies)


def test_seeded_command_sampling_and_override():
    ranges = [[-.5, .5], [-.2, .2], [-1, 1]]
    with QuadrupedLocomotionEnv(command_ranges=ranges) as env:
        first, _ = env.reset(seed=42)
        second, _ = env.reset(seed=42)
        np.testing.assert_array_equal(first, second)
        assert -.5 <= first[9] <= .5 and -.2 <= first[10] <= .2 and -1 <= first[11] <= 1
        obs, _ = env.reset(seed=42, options={'command': [1, 0, -.5]})
        np.testing.assert_array_equal(obs[9:12], [1, 0, -.5])
        env.set_command([.1, .2, .3])
        np.testing.assert_allclose(env._get_obs()[9:12], [.1, .2, .3])
        detached = env.command
        detached[:] = 2
        np.testing.assert_allclose(env.command, [.1, .2, .3])


@pytest.mark.parametrize('command', [[1, 2], [0, np.nan, 0], [4, 0, 0], [[0, 0, 0]]])
def test_bad_command_does_not_modify_state(command):
    with QuadrupedLocomotionEnv() as env:
        env.reset(seed=0)
        before = env.command
        with pytest.raises(ValueError):
            env.set_command(command)
        np.testing.assert_array_equal(before, env.command)


def test_gym_contract_timeout_and_reward_config_override():
    with QuadrupedLocomotionEnv(max_episode_steps=2,
            reward_config=replace(RewardConfig(), torque_weight=0)) as env:
        check_env(env, skip_render_check=True)
        env.reset(seed=0)
        env.step(np.zeros(12))
        _, _, terminated, truncated, info = env.step(np.zeros(12))
        assert truncated and not terminated
        assert info['reward_terms']['torque'] == 0


def test_section_cli_48d_and_reward_term_totals(tmp_path, capsys):
    import json
    output = tmp_path/'summary.json'
    main(['--section', '12.3', '--policy', 'stand', '--steps', '100',
          '--command', '0', '0', '0', '--output', str(output)])
    report = json.loads(output.read_text())
    assert report['observation_size'] == 48
    assert report['command'] == [0, 0, 0]
    assert report['reward_total'] == pytest.approx(sum(report['reward_term_totals'].values()))


def test_reset_metadata_names_the_locomotion_observation():
    with QuadrupedLocomotionEnv() as env:
        _, info = env.reset(seed=0)
        assert info['observation_mode'] == 'locomotion'


def test_cli_implicit_command_uses_same_validation_as_explicit_command():
    with pytest.raises(SystemExit) as error:
        main(['--section', '12.3', '--target-velocity', '4', '--steps', '1'])
    assert error.value.code == 2


def test_transient_contacts_after_initial_fall_remain_in_penalty():
    # This real 0.2 s frame bounces back clear after briefly hitting other links.
    with QuadrupedLocomotionEnv(frame_skip=100) as env:
        env.reset(seed=0)
        env.data.qpos[2] = .2
        half = math.pi/8
        env.data.qpos[3:7] = [math.cos(half), math.sin(half), 0, 0]
        env.data.qvel[2] = -5
        mujoco.mj_forward(env.model, env.data)
        _, _, terminated, _, info = env.step(np.zeros(12))
        assert terminated
        assert {'base_link', 'fl_calf_link', 'rl_calf_link'} <= set(info['unwanted_contact_bodies'])
        assert info['reward_terms']['collision'] == pytest.approx(-1.4)
