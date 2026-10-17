"""Run with ROS Jazzy sourced and the chapter core package on PYTHONPATH."""
import json
from types import SimpleNamespace

import mujoco
import numpy as np
import pytest
import rclpy
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool

from quadruped_rl_ros.mujoco_bridge import MujocoBridge, ordered_targets,simulation_stamp


@pytest.fixture
def bridge():
    rclpy.init()
    node = MujocoBridge()
    node.timer.cancel()
    try:
        yield node
    finally:
        node.destroy_node()
        rclpy.shutdown()


def capture(node):
    messages = {}
    for name in ('clock', 'imu', 'joint', 'odom', 'status'):
        setattr(node, name + '_pub', SimpleNamespace(
            publish=lambda message, key=name: messages.__setitem__(key, message)))
    return messages


def test_targets_are_absolute_named_radians_and_invalid_is_atomic(bridge):
    env = bridge.env
    target = env.nominal_joint_positions + .1
    message = JointState(name=list(reversed(env.joint_names)), position=target[::-1].tolist())
    bridge._on_targets(message)
    np.testing.assert_array_equal(bridge.targets, target)
    bridge._integrate()
    np.testing.assert_array_equal(env.data.ctrl[env._actuator_ids], target)
    assert env.data.time == pytest.approx(.02)
    assert bridge.command_count == 1
    for bad in (float('nan'), float('inf'), 100.):
        message.position[0] = bad
        bridge._on_targets(message)
        np.testing.assert_array_equal(bridge.targets, target)
    message.name[0] = message.name[1]
    bridge._on_targets(message)
    assert bridge.bad_commands == 4
    assert bridge.command_count == 1


def test_published_sensor_frames_reconstruct_core_48_observations(bridge):
    env = bridge.env
    # Deliberately tilted and yawed pose detects world/body confusion.
    quat = np.array([.8, .2, -.3, .4])
    env.data.qpos[3:7] = quat / np.linalg.norm(quat)
    env.data.qvel[:6] = [.7, -.4, .3, .2, -.1, .5]
    mujoco.mj_forward(env.model, env.data)
    messages = capture(bridge)
    bridge._publish_state()
    imu, joints, odom = messages['imu'], messages['joint'], messages['odom']
    q = imu.orientation
    matrix = np.empty(9)
    mujoco.mju_quat2Mat(matrix, np.array([q.w, q.x, q.y, q.z]))
    vector = lambda item: [item.x, item.y, item.z]
    gravity = matrix.reshape(3, 3).T @ [0., 0., -1.]
    by_name = {name: i for i, name in enumerate(joints.name)}
    reconstructed = np.concatenate([
        vector(odom.twist.twist.linear), vector(imu.angular_velocity), gravity,
        env.command,
        [joints.position[by_name[n]] - p for n, p in zip(env.joint_names, env.default_joint_pos)],
        [joints.velocity[by_name[n]] for n in env.joint_names], env.last_action])
    np.testing.assert_allclose(reconstructed, env._get_obs(), atol=1e-7)
    assert odom.header.frame_id == 'odom'
    assert odom.child_frame_id == imu.header.frame_id == 'base_link'
    assert joints.header.stamp == imu.header.stamp == odom.header.stamp == messages['clock'].clock


def test_wall_timeout_holds_nominal_and_pause_stops_clock(bridge):
    messages = capture(bridge)
    bridge.last_command_wall -= 1.
    bridge._tick()
    assert json.loads(messages['status'].data)['target_stale']
    np.testing.assert_array_equal(bridge.env.data.ctrl[bridge.env._actuator_ids],
                                  bridge.env.nominal_joint_positions)
    previous_clock = messages['clock']
    bridge._on_pause(Bool(data=True))
    bridge._tick()
    assert messages['clock'] is previous_clock
    assert bridge.env.data.time == pytest.approx(.02)
    assert json.loads(messages['status'].data)['paused']


def test_fallen_plant_never_autoresets_and_nonfinite_state_stops(bridge):
    messages = capture(bridge)
    bridge.env.data.qpos[2] = .1
    bridge._tick()
    assert bridge.env.data.time == pytest.approx(.02)
    assert bridge.env.data.qpos[2] < .2
    bridge.env.data.qpos[0] = float('nan')
    with pytest.raises(FloatingPointError):
        bridge._tick()
    assert bridge.failed
    assert json.loads(messages['status'].data)['failed']


def test_old_target_timestamp_cannot_replace_recent_command(bridge):
    bridge.env.data.time=1.
    message=JointState(name=list(bridge.env.joint_names),position=bridge.targets.tolist())
    message.header.stamp=simulation_stamp(.99)
    bridge._on_targets(message)
    target=bridge.targets.copy()
    message.position=(target+.1).tolist()
    message.header.stamp=simulation_stamp(.98)
    bridge._on_targets(message)
    np.testing.assert_array_equal(bridge.targets,target)
    message.header.stamp=simulation_stamp(.1)
    bridge._on_targets(message)
    assert bridge.bad_commands==2 and bridge.command_count==1
