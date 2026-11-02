"""G2 observes native inputs and evidence on separate owned serial executors."""
import threading
import time
import pytest
import rclpy
from rclpy.context import Context
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from probe_navigation_13_5 import NavigationProbe,ProbeReceiver


def test_g2_has_two_serial_owners_without_a_second_clock_subscriber(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    receiver=None
    try:
        assert getattr(probe,'recording_node',None) is not None,'separate serial recording owner missing'
        recorder=probe.recording_node
        assert not any(sub.topic_name=='/clock' for sub in recorder.subscriptions)
        assert sum(sub.topic_name=='/clock' for sub in probe.subscriptions)==1
        receiver=ProbeReceiver(probe)
        assert type(receiver.executor).__name__=='EventsExecutor'
        assert type(receiver.recording_receiver.executor).__name__=='EventsExecutor'
        assert receiver.thread is not receiver.recording_receiver.thread
        assert receiver.shutdown(timeout_sec=2.)
        assert receiver.recording_receiver.closed
        assert not receiver.recording_receiver.thread.is_alive()
        report=receiver.report()
        assert report['closed'] and report['recording']['closed']
        assert not report['thread_alive'] and not report['recording']['thread_alive']
        assert report['error'] is report['recording']['error'] is None
    finally:
        if receiver:assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();context.try_shutdown()


def test_recording_callback_failure_is_sticky_and_both_receivers_join(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    receiver=None;entered=threading.Event()
    try:
        assert getattr(probe,'recording_node',None) is not None
        def fail():entered.set();raise ValueError('recording callback failed')
        probe.recording_node.create_timer(.01,fail,clock=Clock(clock_type=ClockType.STEADY_TIME))
        receiver=ProbeReceiver(probe)
        assert entered.wait(1.)
        deadline=time.monotonic()+1.
        while receiver.recording_receiver.thread.is_alive() and time.monotonic()<deadline:time.sleep(.005)
        with pytest.raises(RuntimeError,match='recording callback failed'):receiver.check()
        assert receiver.shutdown(timeout_sec=2.)
        with pytest.raises(RuntimeError,match='recording callback failed'):receiver.check()
    finally:
        if receiver:assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();context.try_shutdown()


def test_unfinished_recording_callback_retains_both_ros_owners(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    entered,release=threading.Event(),threading.Event();receiver=None
    try:
        def blocked():entered.set();assert release.wait(3.)
        probe.recording_node.create_timer(.01,blocked,clock=Clock(clock_type=ClockType.STEADY_TIME))
        receiver=ProbeReceiver(probe)
        assert entered.wait(1.)
        assert not receiver.shutdown(timeout_sec=.01)
        assert not receiver.closed and not receiver.recording_receiver.closed
        assert receiver.recording_receiver.thread.is_alive()
        assert probe.recording_node.context.ok() and probe.context.ok()
        release.set()
        assert receiver.shutdown(timeout_sec=2.)
    finally:
        release.set()
        if receiver:assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();context.try_shutdown()


def test_legacy_probe_api_keeps_original_single_serial_default(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',context=context);receiver=None
    try:
        assert probe.recording_node is None
        receiver=ProbeReceiver(probe)
        assert type(receiver.executor).__name__=='EventsExecutor'
        assert receiver.recording_receiver is None
        assert receiver.shutdown(timeout_sec=2.)
    finally:
        if receiver:assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();context.try_shutdown()
