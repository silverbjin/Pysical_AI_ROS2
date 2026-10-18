"""Real ROS action/service boundaries; not a physics or tracking-accuracy test."""
import json
from pathlib import Path
import subprocess
import threading
import time

from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import TransformStamped
from integrated_robot_interfaces.action import PickObject
from integrated_robot_interfaces.msg import TrackedTarget
import rclpy
import pytest
from rclpy.action import ActionServer, CancelResponse
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, JointState
from std_msgs.msg import String
from std_srvs.srv import SetBool, Trigger
from trajectory_msgs.msg import JointTrajectory
from types import SimpleNamespace

from integrated_robot_runtime.common import DrainingExecutor
from integrated_robot_runtime.manipulation import ManipulationNode
from integrated_robot_runtime.policy import ARM_NAMES, LEG_NAMES, STAND


def wait(predicate, timeout=3.):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.005)
    assert predicate(), 'ROS boundary condition did not arrive'


@pytest.mark.parametrize('stop', ['operator', 'loss', 'lifecycle', 'foreign', 'shutdown'])
def test_default_off_exclusive_session_and_disable_cancels_without_successor(stop):
    rclpy.init(domain_id=148)
    node, peer, executor, thread = None, None, None, None
    stopping = threading.Event()
    try:
        node, peer = ManipulationNode(), Node('tracking_action_peer')
        assert hasattr(node, 'tracking'), 'missing runtime tracking integration'
        goals, cancellations = [], []

        def execute(handle):
            goals.append(handle.request)
            deadline = time.monotonic()+2.
            while time.monotonic() < deadline and not handle.is_cancel_requested:
                time.sleep(.005)
            if handle.is_cancel_requested:
                cancellations.append(True)
                handle.canceled()
            else:
                handle.succeed()
            return FollowJointTrajectory.Result(error_code=0)

        server = ActionServer(peer, FollowJointTrajectory,
                              '/arm_trajectory_controller/follow_joint_trajectory', execute,
                              cancel_callback=lambda _: CancelResponse.ACCEPT,
                              callback_group=node.group)
        executor = DrainingExecutor(num_threads=6)
        executor.add_node(node)
        executor.add_node(peer)
        def spin():
            while not stopping.is_set():
                executor.spin_once(timeout_sec=.01)

        thread = threading.Thread(target=spin)
        thread.start()
        toggle = peer.create_client(SetBool, '/manipulation_node/set_visual_tracking')
        stow = peer.create_client(Trigger, '/manipulation_node/stow')
        assert toggle.wait_for_service(timeout_sec=3)
        time.sleep(.1)
        assert goals == []
        rejected = toggle.call_async(SetBool.Request(data=True))
        wait(rejected.done)
        assert not rejected.result().success  # inactive and missing all inputs
        pkg = Path(__file__).resolve().parents[2] / 'integrated_robot_description'
        xml = subprocess.run(['xacro', str(pkg/'urdf/robot_system.urdf.xacro'),
                              'vision_enabled:=true'], check=True, capture_output=True, text=True).stdout
        node.tracking.on_model(String(data=xml))
        transform = TransformStamped()
        transform.header.frame_id, transform.child_frame_id = 'base_link', 'odom'
        transform.transform.rotation.w = 1.
        node.tracking.buffer.set_transform_static(transform, 'boundary-test-only')
        node.on_activate(None)
        node.safe = True  # This boundary test bypasses physical stow; engine test must not.
        info = CameraInfo(width=320, height=240, distortion_model='plumb_bob')
        info.header.frame_id = 'camera_optical_frame'
        info.k = [277., 0., 160., 0., 277., 120., 0., 0., 1.]
        info.r = [1., 0., 0., 0., 1., 0., 0., 0., 1.]
        info.header.stamp = node.get_clock().now().to_msg()
        node.tracking.on_info(info)
        node.tracking.on_legs(String(data=json.dumps(dict(active=True, ready=True, mode='STAND'))))
        joints = JointState(name=list(ARM_NAMES+LEG_NAMES), position=[0.]*6+list(STAND))
        joints.header.stamp = node.get_clock().now().to_msg()
        node.on_joints(joints)
        target = TrackedTarget(valid=True, status='TRACKED', track_id='one', class_id='fixture', score=.9)
        target.header.frame_id, target.source_header.frame_id = 'odom', 'camera_optical_frame'
        target.header.stamp = target.source_header.stamp = node.get_clock().now().to_msg()
        target.position.x, target.position.y, target.position.z = .90, .02, .35
        node.tracking.on_target(target)
        enabled = toggle.call_async(SetBool.Request(data=True))
        wait(enabled.done)
        assert enabled.result().success, enabled.result().message
        wait(lambda: bool(goals))
        assert goals[0].trajectory.joint_names == list(ARM_NAMES)
        assert max(abs(v) for v in goals[0].trajectory.points[0].positions) <= .04
        blocked = stow.call_async(Trigger.Request())
        wait(blocked.done)
        assert not blocked.result().success
        pick = PickObject.Goal(object_name='fixture', dry_run=True)
        pick.target_pose.header.frame_id = 'base_link'
        pick.target_pose.header.stamp = node.get_clock().now().to_msg()
        pick.target_pose.pose.orientation.w = 1.
        assert node.accept_goal(pick).name == 'REJECT'
        if stop == 'operator':
            disabled = toggle.call_async(SetBool.Request(data=False))
            wait(disabled.done)
            assert disabled.result().success
        elif stop == 'loss':
            target.valid, target.status = False, 'LOST'  # identical last capture stamp
            node.tracking.on_target(target)
        elif stop == 'lifecycle':
            node.on_deactivate(None)
        elif stop == 'shutdown':
            node.begin_shutdown()
        else:
            external = peer.create_publisher(JointTrajectory,
                                             '/arm_trajectory_controller/joint_trajectory', 10)
        wait(lambda: bool(cancellations))
        wait(lambda: node.arm_owner.pending is None)
        time.sleep(.25)
        assert len(goals) == 1 and not node.tracking.guard.enabled
        assert node.tracking.guard.arm_available
    finally:
        stopping.set()
        if thread is not None:
            thread.join(timeout=5)
            assert not thread.is_alive()
        if executor is not None:
            executor.shutdown(timeout_sec=5)
        if peer is not None:
            peer.destroy_node()
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


def test_failed_action_result_latches_tracking_off_instead_of_retrying():
    rclpy.init(domain_id=148)
    node = ManipulationNode()
    try:
        tracking = node.tracking
        token = tracking.guard.enable(dict.fromkeys(tracking.guard.CONDITIONS, True))
        tracking.token = token
        tracking.guard.reserve(token)
        tracking.session = node.busy = True
        tracking.record = SimpleNamespace(terminal=True, result=SimpleNamespace(status=6),
                                           error='controller aborted')
        tracking._release()
        assert not tracking.guard.enabled
        assert 'failed' in tracking.guard.reason
    finally:
        node.destroy_node()
        rclpy.shutdown()


def test_malformed_model_is_not_ready_without_escaping_the_ros_callback():
    rclpy.init(domain_id=148)
    node = ManipulationNode()
    try:
        node.tracking.on_model(String(data='<robot'))
        assert node.tracking.chain is None and not node.tracking.guard.enabled
    finally:
        node.destroy_node()
        rclpy.shutdown()
