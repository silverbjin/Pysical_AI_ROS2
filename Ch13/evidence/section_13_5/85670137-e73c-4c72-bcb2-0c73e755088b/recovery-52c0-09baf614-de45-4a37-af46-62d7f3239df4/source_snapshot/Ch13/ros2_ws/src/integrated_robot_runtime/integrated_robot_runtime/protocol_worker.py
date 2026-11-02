"""One bounded blocking protocol operation; no motor command ownership here."""
import threading

from rclpy.task import Future


class ProtocolWorker:
    def __init__(self, node):
        self.node = node
        self.lock = threading.Lock()
        self.thread = None
        self.pending = self.closed = False

    @property
    def idle(self):
        with self.lock:
            return not self.pending and not (self.thread and self.thread.is_alive())

    async def run(self, function, *args):
        with self.lock:
            if self.closed or self.pending or (self.thread and self.thread.is_alive()):
                raise RuntimeError('protocol worker unavailable; no queued retry')
            self.pending = True
            future = Future(executor=self.node.executor)

            def work():
                try:
                    future.set_result(function(*args))
                except Exception as exc:
                    future.set_exception(exc)

            self.thread = threading.Thread(target=work, name='ch13-bounded-protocol')
            self.thread.start()
        try:
            return await future
        finally:
            with self.lock:
                self.pending = False

    def close(self):
        with self.lock:
            self.closed = True
            thread = self.thread
        if thread is not None:
            thread.join(timeout=2.)
            if thread.is_alive():
                raise RuntimeError('protocol worker still running; ROS destruction refused')
