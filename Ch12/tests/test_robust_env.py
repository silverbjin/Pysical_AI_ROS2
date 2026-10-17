"""Real physics regression contracts for the optional robustness wrapper."""
import numpy as np
import pytest

from quadruped_rl.locomotion_env import QuadrupedLocomotionEnv
from quadruped_rl.robust_env import RobustQuadrupedEnv


def test_disabled_is_baseline_equivalent():
    with QuadrupedLocomotionEnv() as base, RobustQuadrupedEnv(enabled=False) as robust:
        np.testing.assert_array_equal(base.reset(seed=12)[0], robust.reset(seed=12)[0])
        for _ in range(8):
            a = np.full(12, .02)
            left, right = base.step(a), robust.step(a)
            np.testing.assert_array_equal(left[0], right[0])
            assert left[1:4] == right[1:4]


def test_two_step_action_and_observation_impulses():
    with RobustQuadrupedEnv(randomize_dynamics=False, sensor_noise=False,
                             push_probability=0) as env:
        reset, _ = env.reset(seed=4)
        observations = []
        for value in [.1, .2, .3, .4]:
            obs, _, _, _, info = env.step(np.full(12, value))
            observations.append(obs)
            expected = [0, 0, .1, .2][len(observations)-1]
            np.testing.assert_allclose(info['delayed_action'], expected)
            np.testing.assert_allclose(env.unwrapped.last_action, expected)
            np.testing.assert_array_equal(obs, env._get_obs())
        np.testing.assert_array_equal(observations[0], reset)
        np.testing.assert_array_equal(observations[1], reset)
        np.testing.assert_allclose(observations[2][36:48], 0)
        np.testing.assert_allclose(observations[3][36:48], 0)


def test_randomization_seed_originals_and_pd_consistency():
    with RobustQuadrupedEnv() as env:
        model = env.unwrapped.model
        original_mass = model.body_mass.copy()
        original_inertia = model.body_inertia.copy()
        original_gain = model.actuator_gainprm.copy()
        original_bias = model.actuator_biasprm.copy()
        original_limit = model.actuator_forcerange.copy()
        first, info = env.reset(seed=21)
        masses = model.body_mass.copy()
        state = model.body_inertia.copy()
        second, repeated = env.reset(seed=21)
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(masses, model.body_mass)
        np.testing.assert_array_equal(state, model.body_inertia)
        assert info['domain_randomization'] == repeated['domain_randomization']
        ids = env.robot_body_ids
        ratio = masses[ids]/original_mass[ids]
        assert np.all((ratio >= .8) & (ratio <= 1.2))
        np.testing.assert_allclose(state[ids], original_inertia[ids]*ratio[:, None])
        other = np.setdiff1d(np.arange(model.nbody), ids)
        np.testing.assert_array_equal(model.body_mass[other], original_mass[other])
        strength = info['domain_randomization']['actuator_strength']
        np.testing.assert_allclose(model.actuator_gainprm, original_gain*strength)
        np.testing.assert_allclose(model.actuator_biasprm, original_bias*strength)
        np.testing.assert_allclose(model.actuator_forcerange, original_limit*strength)
        friction = info['domain_randomization']['friction_factor']
        assert .5 <= friction <= 1.5
        for geom in [env.unwrapped._ground_geom, *env.unwrapped._foot_geoms]:
            np.testing.assert_allclose(model.geom_friction[geom], env.original_friction[geom]*friction)


@pytest.mark.parametrize('task,dim', [('locomotion',48),('goal',48),('avoidance',64)])
def test_noise_preserves_semantics_and_optional_tasks(task, dim):
    with RobustQuadrupedEnv(task=task, observation_delay=0, action_delay=0,
                             push_probability=0) as env:
        obs, _ = env.reset(seed=51)
        clean = env.unwrapped._get_obs()
        assert obs.shape == (dim,)
        np.testing.assert_array_equal(obs[9:12], clean[9:12])
        np.testing.assert_array_equal(obs[36:], clean[36:])
        assert np.linalg.norm(obs[6:9]) == pytest.approx(1, abs=1e-6)
        assert not np.array_equal(obs[:6], clean[:6])
        np.testing.assert_array_equal(obs, env._get_obs())


def test_world_force_is_applied_for_control_interval_then_cleared():
    with RobustQuadrupedEnv(randomize_dynamics=False, sensor_noise=False,
                             action_delay=0, observation_delay=0, push_probability=1) as env:
        env.reset(seed=7)
        _, _, _, _, info = env.step(np.zeros(12))
        assert np.any(np.abs(info['external_force_world']) > 0)
        assert np.all(np.abs(info['external_force_world']) <= 50)
        np.testing.assert_array_equal(env.unwrapped.data.xfrc_applied, 0)
        np.testing.assert_array_equal(env.unwrapped.data.qfrc_applied, 0)
        env.push_probability = 0
        assert env.step(np.zeros(12))[4]['external_force_world'] == [0.,0.,0.]
        env.reset(seed=7)
        np.testing.assert_array_equal(env.unwrapped.data.xfrc_applied, 0)


def test_push_changes_actual_physics():
    config = dict(randomize_dynamics=False,sensor_noise=False,action_delay=0,observation_delay=0)
    with RobustQuadrupedEnv(push_probability=0, **config) as plain, RobustQuadrupedEnv(push_probability=1, **config) as push:
        plain.reset(seed=17)
        push.reset(seed=17)
        plain.step(np.zeros(12))
        push.step(np.zeros(12))
        assert not np.allclose(plain.unwrapped.data.qvel[:3],push.unwrapped.data.qvel[:3])


def test_torque_motor_strength_is_applied_once():
    with RobustQuadrupedEnv(control_mode='torque',sensor_noise=False,
            action_delay=0,observation_delay=0,push_probability=0) as env:
        _,info = env.reset(seed=35)
        strength = info['domain_randomization']['actuator_strength']
        env.step(np.full(12,.1))
        np.testing.assert_allclose(env.unwrapped.data.actuator_force,
                                   np.tile([2.,3.,3.],4)*strength)


def test_reset_flushes_latency_and_goal_mocap_stays_kinematic():
    with RobustQuadrupedEnv(task='goal',push_probability=0) as env:
        core = env.unwrapped
        target = core.model.body('target').id
        original = core.model.body_mass[target]
        env.reset(seed=10)
        env.step(np.ones(12))
        reset,_ = env.reset(seed=11)
        obs,_,_,_,info = env.step(np.zeros(12))
        np.testing.assert_array_equal(obs,reset)
        np.testing.assert_array_equal(info['delayed_action'],0)
        assert core.model.body_mass[target] == original
        assert target not in env.robot_body_ids


@pytest.mark.parametrize('task', ['locomotion','goal','avoidance'])
def test_dynamics_reset_preserves_seeded_pose_velocity_and_mocap(task):
    with RobustQuadrupedEnv(task=task,randomize_dynamics=False,sensor_noise=False,
            action_delay=0,observation_delay=0,push_probability=0) as baseline, \
         RobustQuadrupedEnv(task=task,randomize_dynamics=True,sensor_noise=False,
            action_delay=0,observation_delay=0,push_probability=0) as randomized:
        baseline_obs,_ = baseline.reset(seed=4)
        obs,info = randomized.reset(seed=4)
        a,b = baseline.unwrapped,randomized.unwrapped
        assert b.data.qpos[2] == pytest.approx(.5)
        np.testing.assert_array_equal(a.data.qpos,b.data.qpos)
        np.testing.assert_array_equal(a.data.qvel,b.data.qvel)
        np.testing.assert_array_equal(a.data.ctrl,b.data.ctrl)
        np.testing.assert_array_equal(a.data.mocap_pos,b.data.mocap_pos)
        np.testing.assert_array_equal(a.data.mocap_quat,b.data.mocap_quat)
        np.testing.assert_array_equal(b._get_obs(),obs)
        # LiDAR is refreshed before perturbation; identical geometry/state must
        # still yield exactly the same clean sensor and task observations.
        np.testing.assert_array_equal(baseline_obs,obs)
        ids = randomized.robot_body_ids
        assert not np.array_equal(a.model.body_mass[ids],b.model.body_mass[ids])
        assert not np.array_equal(a.model.body_inertia[ids],b.model.body_inertia[ids])
        assert info['domain_randomization']['mass_factors']


@pytest.mark.parametrize('kwargs', [dict(action_delay=-1),dict(observation_delay=1.5),
    dict(push_probability=2),dict(push_force=-1),dict(task='missing')])
def test_invalid_config(kwargs):
    with pytest.raises((ValueError, TypeError)):
        RobustQuadrupedEnv(**kwargs)


def test_real_ppo_update():
    torch = pytest.importorskip('torch')
    sb3 = pytest.importorskip('stable_baselines3')
    torch.set_num_threads(1)
    with RobustQuadrupedEnv(max_episode_steps=20) as env:
        model = sb3.PPO('MlpPolicy',env,n_steps=16,batch_size=16,n_epochs=1,
                        policy_kwargs=dict(net_arch=[16]),seed=3,device='cpu')
        before = [p.detach().clone() for p in model.policy.parameters()]
        model.learn(32)
        assert any(not torch.equal(a,b) for a,b in zip(before,model.policy.parameters()))
