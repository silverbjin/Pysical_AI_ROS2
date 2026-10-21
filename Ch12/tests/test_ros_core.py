import numpy as np
import pytest
from quadruped_rl.ros_core import ControllerCore,PolicyContract,rotation_from_xyzw
from quadruped_rl import QuadrupedLocomotionEnv


def populate(core,env,now=1.):
    q=env.data.qpos[3:7]
    core.update_imu([q[1],q[2],q[3],q[0]],env.data.qvel[3:6],now)
    names=list(env.joint_names)[::-1]
    core.update_joints(names,env.data.qpos[env._qpos_ids][::-1],env.data.qvel[env._qvel_ids][::-1],now)
    core.update_velocity(env.get_base_linear_velocity(),now)


def test_observation_exactly_matches_training_and_joint_name_order():
    with QuadrupedLocomotionEnv(command=[.3,.1,-.2]) as env:
        expected,_=env.reset(seed=4)
        core=ControllerCore(PolicyContract.from_env(env))
        populate(core,env)
        core.update_command([.3,.1,-.2],1.)
        assert np.array_equal(core.observation(1.),expected)
        target,applied=core.process_action(np.full(12,100.))
        assert np.max(np.abs(target-env.nominal_joint_positions))<=.1+1e-10
        assert np.allclose(applied,(target-env.nominal_joint_positions)/.35)
        assert np.allclose(core.observation(1.)[-12:],applied)


def test_sensor_faults_and_watchdogs():
    with QuadrupedLocomotionEnv() as env:
        env.reset(seed=1)
        core=ControllerCore(PolicyContract.from_env(env))
        with pytest.raises(RuntimeError):core.observation(1.)
        populate(core,env)
        with pytest.raises(RuntimeError):core.observation(2.)
        with pytest.raises(ValueError):core.update_joints(['bad']*12,[0]*12,[0]*12,1.)
        with pytest.raises(ValueError):core.update_imu([0,0,0,0],[0,0,0],1.)
        with pytest.raises(ValueError):core.process_action(np.full(12,np.nan))
        populate(core,env,now=2.)
        core.update_command([1,0,0],1.)
        assert np.all(core.observation(2.)[9:12]==0) # old cmd_vel becomes stand command
        with pytest.raises(RuntimeError):core.observation(1.) # clock reset/future data


def test_older_samples_do_not_replace_newer_samples():
    with QuadrupedLocomotionEnv() as env:
        env.reset(seed=1)
        core=ControllerCore(PolicyContract.from_env(env));populate(core,env,2.)
        before=core.observation(2.)
        with pytest.raises(ValueError):core.update_velocity([1,0,0],1.99)
        with pytest.raises(ValueError):core.update_imu([0,0,0,1],[1,0,0],1.99)
        with pytest.raises(ValueError):core.update_joints(env.joint_names,[0]*12,[0]*12,1.99)
        assert np.array_equal(core.observation(2.),before)
        core.reset_timing();populate(core,env,1.)
        assert core.observation(1.).shape==(48,)


def test_body_velocity_and_quaternion_conventions():
    rot=rotation_from_xyzw([0,0,np.sin(np.pi/4),np.cos(np.pi/4)])
    assert np.allclose(rot.T@np.array([1,0,0]),[0,-1,0],atol=1e-10)
    with QuadrupedLocomotionEnv() as env:
        env.reset(seed=2)
        core=ControllerCore(PolicyContract.from_env(env))
        populate(core,env)
        core.update_imu([0,0,np.sin(np.pi/4),np.cos(np.pi/4)],[0,0,0],1.)
        core.update_velocity([1,0,0],1.,frame='world')
        assert np.allclose(core.observation(1.)[:3],[0,-1,0],atol=1e-6)


def test_older_command_cannot_override_newer_and_clock_reset_rearms():
    with QuadrupedLocomotionEnv() as env:
        env.reset(seed=4)
        core = ControllerCore(PolicyContract.from_env(env))
        core.update_command([1, 0, 0], 2.)
        with pytest.raises(ValueError, match='Out-of-order command'):
            core.update_command([0, 0, 0], 1.)
        np.testing.assert_array_equal(core.command, [1, 0, 0])
        assert core.command_stamp == 2.
        core.reset_timing()
        core.update_command([0, 0, 0], 1.)
        assert core.command_stamp == 1.
