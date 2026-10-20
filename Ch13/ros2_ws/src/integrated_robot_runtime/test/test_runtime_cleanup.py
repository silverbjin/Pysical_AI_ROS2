"""Constructor errors must still close the context initialized by the executable."""
import signal

import pytest
import rclpy

from integrated_robot_runtime.common import spin


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
