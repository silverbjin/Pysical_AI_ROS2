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
from rclpy.parameter import Parameter
from sensor_msgs.msg import CameraInfo, JointState
from std_msgs.msg import String
from std_srvs.srv import SetBool, Trigger
from trajectory_msgs.msg import JointTrajectory
from types import SimpleNamespace
from unittest.mock import patch

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


def test_enable_and_disable_ack_are_published_even_before_any_control_tick():
    # Characterizes the lost <200ms session: real ROS publisher, no timer tick
    # or action server. Safety predicates are covered by the boundary tests below.
    from rclpy.executors import SingleThreadedExecutor
    rclpy.init(domain_id=148)
    node, peer = ManipulationNode(), Node('tracking_ack_peer')
    executor = SingleThreadedExecutor()
    executor.add_node(peer)
    states = []
    sub = peer.create_subscription(String, '/architecture/visual_tracking',
                                    lambda msg: states.append(json.loads(msg.data)), 10)
    try:
        deadline = time.monotonic()+1.
        while node.count_subscribers('/architecture/visual_tracking') < 1 and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.01)
        tracking = node.tracking
        tracking.joints.append((1, time.monotonic(), dict.fromkeys(ARM_NAMES, 0.), list(STAND)))
        node.safe = True
        with patch.object(tracking, 'conditions', return_value=dict.fromkeys(tracking.guard.CONDITIONS, True)):
            response = tracking.toggle(SetBool.Request(data=True), SetBool.Response())
        assert response.success
        tracking.toggle(SetBool.Request(data=False), SetBool.Response())
        deadline = time.monotonic()+.5
        while len(states) < 2 and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.01)
        assert [v['enabled'] for v in states] == [True, False]
        assert states[0]['event'] == 'enable_ack'
        assert states[0]['inputs']['target_capture_ns'] == 0
        assert states[0]['inputs']['leg_positions'] == list(STAND)
        assert states[0]['inputs']['joint_capture_ns'] == 1
        assert states[1]['generation'] > states[0]['generation']
    finally:
        executor.shutdown()
        peer.destroy_node()
        node.destroy_node()
        rclpy.try_shutdown()


def test_control_timer_does_not_fill_executor_with_callbacks_waiting_on_same_lock():
    rclpy.init(domain_id=148)
    node = ManipulationNode()
    executor = DrainingExecutor(num_threads=4)
    executor.add_node(node)
    stopping, entered = threading.Event(), threading.Event()
    active, maximum = 0, 0
    count_lock = threading.Lock()
    original = node.tracking.timer.callback

    def measured_tick():
        nonlocal active, maximum
        with count_lock:
            active += 1
            maximum = max(maximum, active)
        entered.set()
        try:
            original()
        finally:
            with count_lock:
                active -= 1

    def spin():
        while not stopping.is_set():
            executor.spin_once(timeout_sec=.01)

    node.tracking.timer.callback = measured_tick
    thread = threading.Thread(target=spin)
    try:
        with node.lock:
            thread.start()
            assert entered.wait(timeout=1.)
            time.sleep(.12)  # real contention: every tick waits on the production lock
        stopping.set()
        thread.join(timeout=2.)
        executor.shutdown(timeout_sec=3.)
        assert maximum == 1, f'{maximum} control ticks occupied the executor simultaneously'
    finally:
        stopping.set()
        thread.join(timeout=2.)
        executor.shutdown(timeout_sec=3.)
        node.destroy_node()
        rclpy.try_shutdown()


@pytest.mark.parametrize('stop', ['operator', 'loss', 'lifecycle', 'foreign', 'shutdown', 'camera_motion',
                                 'compute_expiry', 'compute_isolation'])
def test_default_off_exclusive_session_and_disable_cancels_without_successor(stop):
    rclpy.init(domain_id=148)
    node, peer, executor, thread = None, None, None, None
    stopping = threading.Event()
    try:
        node = ManipulationNode(parameter_overrides=[
            Parameter('allow_camera_motion_test', value=stop == 'camera_motion'),
            Parameter('trace_enabled', value=stop == 'compute_expiry'),
            Parameter('trace_run_id', value='424240ff-0bfe-4a4b-92d4-93f6a78d49b8')])
        peer = Node('tracking_action_peer')
        assert hasattr(node, 'tracking'), 'missing runtime tracking integration'
        goals, cancellations, commands, goal_ids = [], [], [], []

        def execute(handle):
            goals.append(handle.request)
            goal_ids.append(bytes(handle.goal_id.uuid).hex())
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
        audit = peer.create_subscription(String, '/architecture/arm_command',
                                          lambda m: commands.append(json.loads(m.data)), 10)
        from rclpy.qos import qos_profile_sensor_data
        traces = []
        trace_sub = peer.create_subscription(String, '/architecture/tracking_trace',
            lambda m: traces.append(json.loads(m.data)), qos_profile_sensor_data)
        executor = DrainingExecutor(num_threads=6)
        executor.add_node(node)
        executor.add_node(peer)
        def spin():
            while not stopping.is_set():
                executor.spin_once(timeout_sec=.01)

        thread = threading.Thread(target=spin)
        thread.start()
        path = '/manipulation_node/set_camera_motion_test' if stop == 'camera_motion' else (
            '/manipulation_node/set_visual_tracking')
        toggle = peer.create_client(SetBool, path)
        stow = peer.create_client(Trigger, '/manipulation_node/stow')
        assert toggle.wait_for_service(timeout_sec=3)
        time.sleep(.1)
        assert goals == []
        assert commands == []
        rejected = toggle.call_async(SetBool.Request(data=True))
        wait(rejected.done)
        assert not rejected.result().success  # inactive and missing all inputs
        pkg = Path(__file__).resolve().parents[2] / 'integrated_robot_description'
        xml = subprocess.run(['xacro', str(pkg/'urdf/robot_system.urdf.xacro'),
                              'vision_enabled:=true'], check=True, capture_output=True, text=True).stdout
        node.tracking.on_model(String(data=xml))
        # Service discovery does not establish action-server discovery.
        # Wait before timestamping the fresh300ms fixtures, then enable once.
        assert node.trajectory.wait_for_server(timeout_sec=3)
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
        if stop in ('compute_expiry', 'compute_isolation'):
            calculate = node.tracking.current_goal
            computing, release_compute = threading.Event(), threading.Event()

            def delayed_calculation(*args, **kwargs):
                values = calculate(*args, **kwargs)
                if stop == 'compute_expiry':
                    time.sleep(.31)  # real elapsed computation, not a mocked motor publisher
                else:
                    computing.set()
                    release_compute.wait(timeout=1.)
                return values

            node.tracking.current_goal = delayed_calculation
        enabled = toggle.call_async(SetBool.Request(data=True))
        wait(enabled.done)
        assert enabled.result().success, enabled.result().message
        if stop == 'compute_isolation':
            assert computing.wait(timeout=1.)
            target.valid, target.status = False, 'LOST'
            ingress = threading.Thread(target=node.tracking.on_target, args=(target,))
            ingress.start()
            try:
                ingress.join(timeout=.1)
                assert not ingress.is_alive(), 'servo calculation blocked safety input ingress'
                assert not node.tracking.guard.enabled
            finally:
                release_compute.set()
                ingress.join(timeout=2.)
            time.sleep(.1)
            assert goals == [] and commands == [], 'late computation dispatched after invalidation'
            return
        if stop == 'compute_expiry':
            time.sleep(.6)
            assert goals == [] and commands == []
            assert not node.tracking.guard.enabled
            wait(lambda: any(v['outcome'] == 'GATE_LOST' for v in traces))
            lost = next(v for v in traces if v['outcome'] == 'GATE_LOST')
            assert lost['ros_now_ns']-lost['capture_ns'] > 300_000_000
            assert lost['times_ns']['gate_lost']-lost['times_ns']['decision'] > 300_000_000
            return
        wait(lambda: bool(goals))
        wait(lambda: bool(commands))
        assert commands[0]['goal_uuid'] == goal_ids[0]
        assert commands[0]['positions'] == list(goals[0].trajectory.points[0].positions)
        assert commands[0]['joint_names'] == list(ARM_NAMES)
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
        if stop in ('operator', 'camera_motion'):
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


def test_new_input_does_not_renew_computed_targets_wall_deadline(monkeypatch):
    """Capture age and joint age can be fresh while the computed target's wall TTL expires."""
    import uuid
    rclpy.init(domain_id=148)
    node = ManipulationNode()
    try:
        tracking = node.tracking
        tracking.timer.cancel()
        tracking.chain = object()
        tracking.reference = dict.fromkeys(ARM_NAMES, 0.)
        tracking.target = TrackedTarget(valid=True)
        tracking.target.header.stamp = node.get_clock().now().to_msg()
        tracking.target_at = time.monotonic()-.29
        tracking.joints.append((node.get_clock().now().nanoseconds, time.monotonic(),
                                tracking.reference.copy(), list(STAND)))
        # Isolate the dispatch boundary: all unrelated lifecycle/TF/model gates
        # are already satisfied, and the selected joint remains fresh.
        monkeypatch.setattr(tracking, 'conditions', lambda *_:
                            dict.fromkeys(tracking.guard.CONDITIONS, True))
        tracking.token = tracking.guard.enable(dict.fromkeys(tracking.guard.CONDITIONS, True))
        tracking.session = node.busy = True

        def calculate(now, wall, work):
            time.sleep(.04)
            tracking.target_at = time.monotonic()  # a newer input is received during computation
            return tracking.reference.copy(), work['joints'][-1]

        monkeypatch.setattr(tracking, 'current_goal', calculate)
        # No physical transport is attached to this boundary characterization.
        monkeypatch.setattr(node.arm_owner, 'send', lambda *_args, **_kwargs:
                            SimpleNamespace(identifier=uuid.uuid4().bytes, terminal=False))
        tracking._tick()
        assert tracking.goal_count == 0, 'new input renewed the old computation wall TTL'
        assert not tracking.guard.enabled
        assert 'expired' in tracking.guard.reason
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def test_malformed_model_is_not_ready_without_escaping_the_ros_callback():
    rclpy.init(domain_id=148)
    node = ManipulationNode()
    try:
        node.tracking.on_model(String(data='<robot'))
        assert node.tracking.chain is None and not node.tracking.guard.enabled
    finally:
        node.destroy_node()
        rclpy.shutdown()


def test_camera_motion_benchmark_requires_explicit_test_opt_in():
    rclpy.init(domain_id=148)
    node = ManipulationNode()
    try:
        response = node.tracking.toggle_motion(SetBool.Request(data=True), SetBool.Response())
        assert not response.success and 'disabled' in response.message.lower()
        assert not node.tracking.guard.enabled and node.arm_owner.pending is None
    finally:
        node.destroy_node()
        rclpy.shutdown()


def test_trace_failure_does_not_renew_or_disable_target(monkeypatch):
    rclpy.init(domain_id=148)
    node = ManipulationNode(parameter_overrides=[
        Parameter('trace_enabled', value=True),
        Parameter('trace_run_id', value='424240ff-0bfe-4a4b-92d4-93f6a78d49b8')])
    try:
        tracking = node.tracking
        assert hasattr(tracking, 'trace'), 'missing isolated tracking trace hook'
        def fail(_):
            raise RuntimeError('diagnostic transport failure')
        monkeypatch.setattr(tracking.trace.publisher, 'publish', fail)
        target = TrackedTarget(valid=True, status='TRACKED', track_id='one', class_id='fixture', score=.9)
        target.header.frame_id, target.source_header.frame_id = 'odom', 'camera_optical_frame'
        target.header.stamp = target.source_header.stamp = node.get_clock().now().to_msg()
        target.position.x = .9
        tracking.on_target(target)
        received = tracking.target_at
        token = tracking.guard.enable(dict.fromkeys(tracking.guard.CONDITIONS, True))
        tracking.on_target(target)  # same capture must not renew receipt TTL
        assert tracking.target_at == received and tracking.target is target
        assert tracking.guard.enabled and tracking.guard.generation == token
        assert tracking.trace.stats['errors'] >= 1
        assert node.arm_owner.pending is None
        tracking.guard.disable('test end')
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def test_trace_serialization_runs_outside_control_lock(monkeypatch):
    rclpy.init(domain_id=148)
    node = ManipulationNode(parameter_overrides=[
        Parameter('trace_enabled', value=True),
        Parameter('trace_run_id', value='424240ff-0bfe-4a4b-92d4-93f6a78d49b8')])
    observed = []
    try:
        assert hasattr(node.tracking, 'trace'), 'missing control trace hook'
        original = node.tracking.trace.emit
        def checked(*args, **kwargs):
            # RLock.acquire on another thread detects ownership, including nested calls.
            acquired = []
            def probe():
                locked = node.lock.acquire(timeout=.05)
                acquired.append(locked)
                if locked:
                    node.lock.release()
            probe_thread = threading.Thread(target=probe)
            probe_thread.start()
            probe_thread.join(timeout=.2)
            assert acquired == [True], 'trace serialization ran under control lock'
            observed.append(kwargs)
            return original(*args, **kwargs)
        monkeypatch.setattr(node.tracking.trace, 'emit', checked)
        node.tracking.tick()
        assert observed and observed[-1]['capture_ns'] is None
        assert observed[-1]['times_ns']['decision'] > 0
        assert node.arm_owner.pending is None
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def test_tracking_trace_closes_before_context_shutdown():
    import sys
    code = '''
import rclpy
from rclpy.parameter import Parameter
from integrated_robot_runtime.manipulation import ManipulationNode
rclpy.init(domain_id=149)
node = ManipulationNode(parameter_overrides=[
    Parameter('trace_enabled', value=True),
    Parameter('trace_run_id', value='424240ff-0bfe-4a4b-92d4-93f6a78d49b8')])
node.tracking.tick()
node.destroy_node()
rclpy.shutdown()
'''
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=15.)
    assert result.returncode == 0, result.stdout+result.stderr
    output = result.stdout+result.stderr
    assert output.count('trace_totals') == 1
    assert 'context is invalid' not in output, output


def test_target_callback_gate_loss_keeps_last_valid_source_without_a_timer_tick():
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import qos_profile_sensor_data
    rclpy.init(domain_id=148)
    node = ManipulationNode(parameter_overrides=[
        Parameter('trace_enabled', value=True),
        Parameter('trace_run_id', value='424240ff-0bfe-4a4b-92d4-93f6a78d49b8')])
    peer, executor = Node('callback_gate_loss_peer'), SingleThreadedExecutor()
    executor.add_node(peer)  # deliberately never runs node's control timer
    traces = []
    sub = peer.create_subscription(String, '/architecture/tracking_trace',
        lambda m: traces.append(json.loads(m.data)), qos_profile_sensor_data)
    try:
        target = TrackedTarget(valid=True, status='TRACKED', track_id='one', class_id='fixture', score=.9)
        target.header.frame_id, target.source_header.frame_id = 'odom', 'camera_optical_frame'
        target.header.stamp = target.source_header.stamp = node.get_clock().now().to_msg()
        target.position.x = .9
        node.tracking.on_target(target)
        node.tracking.guard.enable(dict.fromkeys(node.tracking.guard.CONDITIONS, True))
        target.valid, target.status = False, 'LOST'
        node.tracking.on_target(target)
        end = time.monotonic()+.2
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.005)
        assert not node.tracking.guard.enabled and node.arm_owner.pending is None
        assert len(traces) == 2
        initial = next(v for v in traces if v['outcome'] == 'TARGET_RECEIVED')
        lost = next((v for v in traces if v['outcome'] == 'GATE_LOST'), None)
        assert lost is not None, 'callback disabled immediately but no gate-loss boundary was emitted'
        assert lost['capture_ns'] == initial['capture_ns']
        assert lost['times_ns']['target_receive'] == initial['times_ns']['target_receive']
        assert lost['times_ns']['gate_lost'] >= lost['times_ns']['decision']
    finally:
        executor.shutdown()
        node.destroy_node()
        peer.destroy_node()
        rclpy.try_shutdown()
