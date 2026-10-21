"""Section 12.2 contracts exercise real position servos and free-base physics."""
import mujoco
import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from quadruped_rl import QuadrupedEnv, QuadrupedTrainingEnv
from quadruped_rl.demo import main, stand_action


def test_draft_import_profile_and_fifty_hz_step():
    from quadruped_env import QuadrupedEnv as DraftEnv
    with DraftEnv() as env:
        assert isinstance(env, QuadrupedTrainingEnv)
        obs, _ = env.reset(seed=42)
        assert obs.shape == (31,) and obs.dtype == np.float32
        assert env.data.qpos[2] == .5
        assert env.metadata['render_fps'] == 50
        np.testing.assert_allclose(obs[:4], [1, 0, 0, 0])
        env.step(np.zeros(12))
        assert env.data.time == pytest.approx(.02)
        np.testing.assert_allclose(env.data.ctrl, [0, -.5, 1] * 4)


def test_quaternion_observation_uses_angular_not_linear_velocity():
    with QuadrupedTrainingEnv() as env:
        env.reset(seed=0)
        env.data.qpos[3:7] = [np.sqrt(.5), 0, 0, np.sqrt(.5)]
        env.data.qvel[:6] = [1, 2, 3, .1, .2, .3]
        mujoco.mj_forward(env.model, env.data)
        obs = env._get_obs()
        np.testing.assert_allclose(obs[:4], [np.sqrt(.5), 0, 0, np.sqrt(.5)])
        np.testing.assert_allclose(obs[4:7], [.1, .2, .3])
        np.testing.assert_allclose(obs[7:19], env.data.qpos[7:])
        np.testing.assert_allclose(obs[19:31], env.data.qvel[6:])


@pytest.mark.parametrize('control', ['position', 'torque'])
def test_checker_and_seed_replay_for_training_profile(control):
    with QuadrupedTrainingEnv(control_mode=control) as env:
        check_env(env, skip_render_check=True)
        first, _ = env.reset(seed=42)
        a = np.linspace(-.2, .2, 12)
        result = env.step(a)
        second, _ = env.reset(seed=42)
        np.testing.assert_array_equal(first, second)
        replay = env.step(a)
        np.testing.assert_array_equal(result[0], replay[0])
        assert result[1:] == replay[1:]


def test_position_clipping_and_actual_force_energy():
    with QuadrupedTrainingEnv() as env:
        env.reset(seed=7)
        _, reward, _, _, info = env.step(np.full(12, 2.0))
        np.testing.assert_allclose(env.data.ctrl, [.35, -.15, 1.35] * 4)
        assert info['action_clipped'] and info['control_mode'] == 'position'
        assert np.all(np.abs(env.data.actuator_force) <= [20, 30, 30] * 4)
        actual = np.mean(np.abs(env.data.actuator_force * env.data.qvel[6:]))
        assert info['reward_terms']['energy'] == pytest.approx(-.002 * actual)
        assert reward == pytest.approx(sum(info['reward_terms'].values()))


def test_position_servo_changes_direction_and_caps_force():
    with QuadrupedTrainingEnv() as env:
        env.reset(seed=0)
        env.data.qpos[7:] = [0, -.5, 1] * 4
        env.data.qvel[:] = 0
        env.data.ctrl[:] = [.35, -.15, 1.35] * 4
        mujoco.mj_forward(env.model, env.data)
        assert env.data.actuator_force[0] == pytest.approx(14)
        assert env.data.actuator_force[1] == pytest.approx(30)
        env.data.ctrl[:] = [-.35, -.85, .65] * 4
        mujoco.mj_forward(env.model, env.data)
        assert env.data.actuator_force[0] == pytest.approx(-14)
        assert env.data.actuator_force[1] == pytest.approx(-30)


def test_training_fall_threshold_and_twenty_second_timeout():
    with QuadrupedTrainingEnv(max_episode_steps=2) as env:
        env.reset(seed=0)
        env.step(np.zeros(12))
        _, _, terminated, truncated, _ = env.step(np.zeros(12))
        assert truncated and not terminated
        env.reset(seed=0)
        env.data.qpos[2] = .19
        mujoco.mj_forward(env.model, env.data)
        assert env.step(np.zeros(12))[2]


def test_position_and_torque_models_share_kinematics():
    with QuadrupedTrainingEnv() as position, QuadrupedTrainingEnv(control_mode='torque') as torque:
        position.reset(seed=42)
        torque.reset(seed=42)
        assert (position.model.nq, position.model.nv, position.model.nu) == (19, 18, 12)
        np.testing.assert_array_equal(position.model.body_mass, torque.model.body_mass)
        np.testing.assert_allclose(position.data.xpos, torque.data.xpos)
        np.testing.assert_array_equal(stand_action(position), np.zeros(12))


@pytest.mark.parametrize('kwargs', [dict(control_mode='invalid'), dict(initial_height=np.nan),
    dict(initial_height=.1, termination_height=.2), dict(termination_height=-1)])
def test_invalid_training_config(kwargs):
    with pytest.raises(ValueError):
        QuadrupedTrainingEnv(**kwargs)


@pytest.mark.parametrize('control', ['position', 'torque'])
def test_nonfinite_state_is_not_hidden_by_mujoco_auto_reset(control):
    with QuadrupedTrainingEnv(control_mode=control) as env:
        env.reset(seed=0)
        env.data.qvel[0] = np.nan
        with pytest.raises(FloatingPointError):
            env.step(np.zeros(12))
        with pytest.raises(RuntimeError):
            env.step(np.zeros(12))
        obs, _ = env.reset(seed=0)
        assert np.isfinite(obs).all()


def test_section_cli_selects_training_defaults(tmp_path, capsys):
    import json
    output = tmp_path/'result.json'
    assert main(['--section', '12.2', '--policy', 'stand', '--steps', '100',
                 '--output', str(output)]) == 0
    report = json.loads(output.read_text())
    assert report['observation_size'] == 31
    assert report['control_mode'] == 'position'
    assert report['physics_seconds'] == 2
    assert report['frame_skip'] == 10


def test_unstable_finite_velocity_reports_failure_instead_of_silent_reset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # MuJoCo may emit MUJOCO_LOG.TXT for this deliberate fault.
    with QuadrupedTrainingEnv() as env:
        env.reset(seed=0)
        env.data.qvel[0] = 1e12
        with pytest.raises(FloatingPointError):
            env.step(np.zeros(12))


@pytest.mark.parametrize('seed', [0, 42, 123])
def test_torque_standing_baseline_remains_upright_for_twenty_seconds(seed):
    with QuadrupedTrainingEnv(control_mode='torque') as env:
        env.reset(seed=seed)
        for _ in range(1000):
            _, _, terminated, _, _ = env.step(stand_action(env))
            assert not terminated


def test_training_profile_rejects_incompatible_observation_overrides():
    with pytest.raises(ValueError, match='31-D'):
        QuadrupedTrainingEnv(observation_mode='textbook')
    with QuadrupedTrainingEnv(observation_mode='quaternion') as env:
        assert env.reset(seed=3)[0].shape == (31,)
