"""Small ROS callbacks, worker ownership, and deferred constructor-time SIGINT."""
import signal
from threading import Event

import rclpy
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.signals import SignalHandlerOptions


def run_node(node_type, *, args=None, executor_factory=SingleThreadedExecutor):
    # Do not raise KeyboardInterrupt between starting a worker and assigning node.
    # Keep the context alive until the constructor returns and workers are joined.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    stopping = Event()
    previous = signal.signal(signal.SIGINT, lambda *_: stopping.set())
    node, executor = None, None
    try:
        node = node_type()
        executor = executor_factory()
        executor.add_node(node)
        while rclpy.ok() and not stopping.is_set():
            executor.spin_once(timeout_sec=.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            if executor is not None:
                executor.shutdown(timeout_sec=2.)
        finally:
            try:
                if node is not None:
                    node.destroy_node()
            finally:
                try:
                    rclpy.try_shutdown()
                finally:
                    signal.signal(signal.SIGINT, previous)
