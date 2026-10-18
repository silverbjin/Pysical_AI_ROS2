"""Executor and timestamp helpers shared by the lab nodes."""
import time
import signal
import threading

import rclpy
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.signals import SignalHandlerOptions


class DrainingExecutor(MultiThreadedExecutor):
    """Jazzy shutdown compatibility: drain callbacks before destroying guards.

    Installed Jazzy Executor.shutdown destroys guard conditions before the
    MultiThreadedExecutor thread pool is joined. A finishing callback can still
    trigger that guard. The pool member is the only private compatibility hook;
    keep this localized and re-test when upgrading rclpy.
    """

    def shutdown(self, timeout_sec=None, *, wait_for_threads=True):
        # spin() has returned, so no further callbacks are submitted here.
        self._executor.shutdown(wait=True)
        return super().shutdown(timeout_sec=timeout_sec, wait_for_threads=wait_for_threads)


def seconds(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


def wait_future(future, timeout, running=lambda: True):
    """Used only in reentrant callbacks with other executor threads available."""
    deadline = time.monotonic() + timeout
    while rclpy.ok() and running() and time.monotonic() < deadline:
        if future.done():
            return future.result()
        time.sleep(0.01)
    raise TimeoutError('ROS operation did not finish before its wall-clock deadline')


def spin(node_type, threads=4):
    # Keep the context alive until callbacks and the bounded worker have stopped.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    stopping = threading.Event()
    # Do not raise KeyboardInterrupt inside a pybind take_message conversion.
    signal.signal(signal.SIGINT, lambda *_: stopping.set())
    node = node_type()
    executor = DrainingExecutor(num_threads=threads)
    executor.add_node(node)
    try:
        # A bounded wait also lets Python process SIGINT on otherwise idle nodes.
        while rclpy.ok() and not stopping.is_set():
            executor.spin_once(timeout_sec=0.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if hasattr(node, 'begin_shutdown'):
            node.begin_shutdown()
            deadline = time.monotonic() + 1.
            while rclpy.ok() and not node.shutdown_ready() and time.monotonic() < deadline:
                executor.spin_once(timeout_sec=.02)
            if not node.shutdown_ready():
                node.get_logger().error(
                    'Arm shutdown cancellation unconfirmed; controller hold is NOT proven')
        executor.shutdown(timeout_sec=10)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
