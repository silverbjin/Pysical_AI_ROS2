"""Real ROS node regressions, using an in-memory policy and canonical plant."""
import json
import time
from types import SimpleNamespace

import numpy as np
import pytest
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState

from quadruped_rl.locomotion_env import QuadrupedLocomotionEnv
from quadruped_rl_ros import rl_controller


class ZeroPolicy:
    def __init__(self):
        self.action = np.zeros(12, dtype=np.float32)

    def predict(self, observation, deterministic=True):
        return self.action.copy(), None


@pytest.fixture
def controller(monkeypatch):
    model = ZeroPolicy()
    monkeypatch.setattr(rl_controller, 'load_bundle', lambda *a, **kw:
        (model, QuadrupedLocomotionEnv(command=[0., 0., 0.]), {'task': 'locomotion'}))
    rclpy.init(args=['--ros-args', '-p', 'enabled:=true', '-p', 'bundle_path:=dummy'])
    node = rl_controller.RLController()
    node.timer.cancel()
    node.watchdog.cancel()
    node.sent_targets = []
    node.sent_status = []
    node.targets_pub = SimpleNamespace(publish=node.sent_targets.append)
    node.status_pub = SimpleNamespace(publish=node.sent_status.append)
    try:
        yield node
    finally:
        node.destroy_node()
        rclpy.shutdown()


def sensor_messages(node):
    stamp = node.get_clock().now().to_msg()
    imu = Imu()
    imu.header.stamp = stamp
    imu.orientation.w = 1.
    joints = JointState()
    joints.header.stamp = stamp
    joints.name = list(node.contract.joint_names)
    joints.position = (node.contract.nominal + .1).tolist()
    joints.velocity = [0.] * 12
    odom = Odometry()
    odom.header.stamp = stamp
    odom.child_frame_id = 'base_link'
    odom.pose.pose.position.z = .5
    return imu, joints, odom


def populate(node):
    imu, joints, odom = sensor_messages(node)
    node.imu_callback(imu)
    node.joint_callback(joints)
    node.odom_callback(odom)
    return imu, joints, odom


def test_startup_action_describes_the_actual_published_ramp(controller):
    node = controller
    populate(node)
    node.control_loop()
    assert node.armed
    assert len(node.sent_targets) == 1
    expected = node.contract.nominal + .1 - node.cfg['startup_velocity'] * node.contract.dt
    np.testing.assert_allclose(node.sent_targets[-1].position, expected)
    np.testing.assert_allclose(node.core.last_target, node.sent_targets[-1].position)
    np.testing.assert_allclose(node.core.last_action,
        (np.asarray(node.sent_targets[-1].position) - node.contract.nominal) / node.contract.action_scale)
    assert np.any(node.core.last_action != 0.)
    status = json.loads(node.sent_status[-1].data)
    assert status['status'] == 'arming'
    np.testing.assert_allclose(status['applied_action'], node.core.last_action)


def test_duplicate_node_name_still_detects_an_external_command_publisher(controller):
    node = controller
    other = Node(node.get_name())
    publisher = other.create_publisher(JointState, '/rl/joint_targets', 10)
    try:
        deadline = time.monotonic() + 5.
        while len(node.get_publishers_info_by_topic('/rl/joint_targets')) < 2:
            assert time.monotonic() < deadline, 'Second DDS publisher was not discovered'
            rclpy.spin_once(node, timeout_sec=.05)
        assert publisher is not None
        node.last_graph_check = 0.
        node.wall_watchdog()
        assert node.conflict
        populate(node)
        node.control_loop()
        assert not node.sent_targets
        assert json.loads(node.sent_status[-1].data)['status'] == 'Multiple command publishers'
    finally:
        other.destroy_node()


@pytest.mark.parametrize('sensor', ['orientation', 'velocity', 'old_imu', 'old_joints', 'old_odom'])
def test_bad_sensor_input_sets_fault_and_blocks_command(controller, sensor):
    node = controller
    imu, joints, odom = populate(node)
    if sensor == 'orientation':
        imu.orientation.w = 0.
        node.imu_callback(imu)
        expected = 'imu'
    elif sensor == 'velocity':
        joints.velocity = []
        node.joint_callback(joints)
        expected = 'joints'
    else:
        message, callback, expected = {
            'old_imu': (imu, node.imu_callback, 'imu'),
            'old_joints': (joints, node.joint_callback, 'joints'),
            'old_odom': (odom, node.odom_callback, 'velocity'),
        }[sensor]
        message.header.stamp.sec -= 1
        callback(message)
    assert expected in node.faults
    node.control_loop()
    assert not node.sent_targets
    assert json.loads(node.sent_status[-1].data)['status'] == 'Invalid input'


def test_nan_inference_publishes_no_command(controller):
    node = controller
    populate(node)
    node.control_loop()
    assert node.armed
    previously_sent = len(node.sent_targets)
    previous_target = node.core.last_target.copy()
    previous_action = node.core.last_action.copy()
    node.model.action[:] = np.nan
    populate(node)
    node.control_loop()
    assert len(node.sent_targets) == previously_sent
    assert node.inferences == 0
    np.testing.assert_array_equal(node.core.last_target, previous_target)
    np.testing.assert_array_equal(node.core.last_action, previous_action)
    assert json.loads(node.sent_status[-1].data)['status'] == 'invalid_inference'
