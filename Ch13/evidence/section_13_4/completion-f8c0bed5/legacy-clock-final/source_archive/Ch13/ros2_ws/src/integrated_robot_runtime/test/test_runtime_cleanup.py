"""Constructor errors must still close the context initialized by the executable."""
import signal
import os
import threading

import pytest
import rclpy

from integrated_robot_runtime.common import spin


def test_one_thread_mode_runs_callback_inline_and_closes_ros():
    """A pool in the one-thread mode reintroduces the measured clock handoff cost."""
    from rclpy.node import Node
    owner = threading.get_ident()
    callbacks = []

    class Probe(Node):
        def __init__(self):
            super().__init__('inline_executor_probe')
            self.timer = self.create_timer(.02, self.finish)

        def finish(self):
            self.timer.cancel()
            callbacks.append(threading.get_ident())
            os.kill(os.getpid(), signal.SIGINT)

    spin(Probe, threads=1)
    assert callbacks == [owner]
    assert not rclpy.ok()


def test_constructor_failure_closes_context_and_restores_sigint_handler():
    previous = signal.getsignal(signal.SIGINT)

    def fail_constructor():
        raise RuntimeError('intentional node constructor failure')

    try:
        with pytest.raises(RuntimeError, match='intentional'):
            spin(fail_constructor)
        assert not rclpy.ok(), 'constructor failure leaked initialized ROS context'
        assert signal.getsignal(signal.SIGINT) == previous
    finally:
        rclpy.try_shutdown()
        signal.signal(signal.SIGINT, previous)
