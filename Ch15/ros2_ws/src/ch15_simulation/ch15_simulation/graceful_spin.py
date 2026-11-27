"""Single-threaded, signal-safe lifecycle for the read-only cube detector."""
import signal

def run_node(factory):
    import rclpy
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.signals import SignalHandlerOptions

    stop = False
    def request_stop(signum, frame):
        nonlocal stop
        stop = True

    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    node = executor = None
    initialized = False
    try:
        for sig in previous:
            signal.signal(sig, request_stop)
        # The Python handler only requests stop. In particular, it must not
        # invalidate the context while a timer callback is still publishing.
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        initialized = True
        if stop:
            return
        node = factory()
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        while not stop and rclpy.ok():
            executor.spin_once(timeout_sec=0.1)
    finally:
        try:
            if executor is not None:
                executor.shutdown()
        finally:
            try:
                if node is not None:
                    node.destroy_node()
            finally:
                try:
                    if initialized:
                        rclpy.try_shutdown()
                finally:
                    for sig, handler in previous.items():
                        signal.signal(sig, handler)
