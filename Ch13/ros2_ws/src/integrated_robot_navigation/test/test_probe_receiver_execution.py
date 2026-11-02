"""Real DDS dispatch while the caller waits; never physical acceptance."""
from pathlib import Path
import sys
import threading
import time

import pytest
import rclpy
from rclpy.context import Context
from rclpy.node import Node

from carry_feedback_peer import CarryFeedbackPeer
from guard_fixture import bundle

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))


def receiver_type():
    import run_navigation_13_5 as runner
    assert hasattr(runner, 'ProbeReceiver'), 'independent owned probe receiver missing'
    return runner.ProbeReceiver


def test_probe_separates_callback_wait_cpu_and_journal_cost(tmp_path):
    """Controlled 15ms wait is telemetry, never a native latency verdict."""
    from probe_navigation_13_5 import NavigationProbe
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',context=context)
    try:
        assert hasattr(probe,'timing_snapshot'),'callback/journal timing boundary missing'
        def controlled_wait():
            time.sleep(.015)
            probe._write('controlled_record',dict(original_capture_ns=123))
        probe._dispatch(controlled_wait)
        report=probe.timing_snapshot()
        row=report['callbacks']['controlled_wait']
        assert row['count']==1 and row['max_wall_ns']>=15_000_000
        assert row['cpu_ns']<row['wall_ns']
        assert report['journal']['controlled_record']['count']==1
        assert report['slow_callbacks'][-1]['callback']=='controlled_wait'
        assert report['scope']=='local_observer_cost_not_dds_queue_or_capture_latency'
    finally:
        probe.close_log();probe.destroy_node();context.try_shutdown()


@pytest.mark.parametrize('engine',['mujoco','gazebo'])
def test_native_capture_diagnostic_requests_reliable_transport(tmp_path,engine):
    """Catch a best-effort consumer silently dropping the gyro reference pair."""
    from probe_navigation_13_5 import NavigationProbe
    from rclpy.qos import ReliabilityPolicy
    context = Context()
    rclpy.init(context=context)
    probe = NavigationProbe(tmp_path, engine=engine, context=context)
    try:
        endpoints = probe.get_subscriptions_info_by_topic('/navigation/native_controls')
        own = [endpoint for endpoint in endpoints if endpoint.node_name == probe.get_name()]
        assert len(own) == 1
        assert own[0].qos_profile.reliability == ReliabilityPolicy.RELIABLE
        # Jazzy RMW discovery reports depth=0 (unknown), not configured depth.
    finally:
        probe.close_log()
        probe.destroy_node()
        rclpy.shutdown(context=context)


def test_probe_ingress_survives_a_blocked_caller_and_joins_before_log_close(tmp_path, nav_robot_model):
    cls = receiver_type()
    from probe_navigation_13_5 import NavigationProbe
    peer = CarryFeedbackPeer(nav_robot_model.model_sha256, bundle(nav_robot_model).joints.data['position'])
    context = Context()
    rclpy.init(context=context)
    probe = NavigationProbe(tmp_path, engine='gazebo', context=context)
    receiver = cls(probe)
    try:
        deadline = time.monotonic()+3.
        sample = None
        while time.monotonic() < deadline:
            with probe._lock:
                sample = probe.inbox.samples['joints']
            if sample is not None:
                break
            time.sleep(.01)
        assert sample is not None
        first_stamp = sample.stamp_ns
        time.sleep(.3)  # caller is blocked, independent DDS source keeps running
        receiver.check()
        with probe._lock:
            sample = probe.inbox.samples['joints']
        assert sample.stamp_ns > first_stamp
        assert time.monotonic_ns()-sample.received_ns < 100_000_000
        assert not probe.frames, 'incomplete test sensor source is never a physical frame'
        assert receiver.shutdown(timeout_sec=2.) and not receiver.thread.is_alive()
        stamp = sample.stamp_ns
        time.sleep(.05)
        with probe._lock:
            assert probe.inbox.samples['joints'].stamp_ns == stamp
    finally:
        assert receiver.shutdown(timeout_sec=2.)
        probe.close_log()
        probe.destroy_node()
        context.try_shutdown()
        peer.close()


def test_probe_callback_failure_is_sticky_and_visible_to_the_caller():
    cls = receiver_type()
    context = Context()
    rclpy.init(context=context)
    node = Node('probe_receiver_failure_peer', context=context)
    entered = threading.Event()

    def fail():
        entered.set()
        raise ValueError('actual callback failure')

    node.create_timer(.01, fail)
    receiver = cls(node)
    try:
        assert entered.wait(1.)
        deadline = time.monotonic()+1.
        while receiver.thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.005)
        with pytest.raises(RuntimeError, match='probe receiver callback failed'):
            receiver.check()
        assert receiver.shutdown(timeout_sec=2.)
        with pytest.raises(RuntimeError, match='probe receiver callback failed'):
            receiver.check()
    finally:
        assert receiver.shutdown(timeout_sec=2.)
        node.destroy_node()
        context.try_shutdown()


def test_unfinished_probe_callback_cannot_be_reported_as_joined():
    cls = receiver_type()
    context = Context()
    rclpy.init(context=context)
    node = Node('probe_receiver_blocked_peer', context=context)
    entered, release = threading.Event(), threading.Event()

    def blocked():
        entered.set()
        assert release.wait(2.)

    node.create_timer(.01, blocked)
    receiver = cls(node)
    try:
        assert entered.wait(1.)
        assert not receiver.shutdown(timeout_sec=.01)
        assert receiver.thread.is_alive(), 'ROS handles must remain alive until the callback finishes'
        release.set()
        assert receiver.shutdown(timeout_sec=2.)
    finally:
        release.set()
        assert receiver.shutdown(timeout_sec=2.)
        node.destroy_node()
        context.try_shutdown()
