"""Owned serial DDS ingress, independent of the model/control thread pool.

The node has no timers, motor publishers or lifecycle services. It may own the
existing TimeSource's one original subscription; it never forwards a clock or
creates a second TimeSource for control. Input callbacks preserve first receipt
and update bounded mailboxes. They may signal one coalesced owner notification;
they never execute the model, retag data or grant motion.
"""
import threading
import os
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node


class IngressDispatch:
    def __init__(self,context,name,namespace,subscriptions,*,autostart=True):
        self.error=None
        self.joined=False
        self.stopping=threading.Event()
        self.node=Node(name,context=context,namespace=namespace,
            use_global_arguments=False,start_parameter_services=False,enable_rosout=False)
        self.node_name=self.node.get_name()
        self.namespace=self.node.get_namespace()
        self.executor=SingleThreadedExecutor(context=context)
        self.thread=threading.Thread(target=self._spin,name=name,daemon=False)
        try:
            for args,kwargs in subscriptions:
                # This receiver is serial; never share the model's callback group.
                kwargs={key:value for key,value in kwargs.items() if key!='callback_group'}
                self.node.create_subscription(*args,**kwargs)
            self.executor.add_node(self.node)
            if autostart:self.start()  # last: no orphan on setup failure
        except BaseException:
            self.executor.shutdown(timeout_sec=2.)
            self.node.destroy_node()
            raise

    def start(self):
        if self.joined or self.thread.ident is not None:
            raise RuntimeError('ingress dispatch cannot restart')
        self.thread.start()

    def _spin(self):
        try:
            while not self.stopping.is_set() and self.node.context.ok():
                self.executor.spin_once(timeout_sec=.02)
        except BaseException as error:
            # Sticky failure. The model owner observes it; never restart ingress.
            self.error=repr(error)

    def close(self):
        if self.joined:return
        self.stopping.set()
        self.executor.wake()
        if self.thread.ident is not None:self.thread.join(timeout=2.)
        if self.thread.is_alive():
            raise RuntimeError('navigation ingress join unconfirmed; ROS resources retained')
        self.executor.shutdown(timeout_sec=2.)
        self.node.destroy_node()
        self.joined=True

    def snapshot(self):
        return dict(dispatch='owned_serial_waitset',alive=self.thread.is_alive(),
            joined=self.joined,error=self.error,pid=os.getpid(),uid=os.getuid(),
            native_tid=self.thread.native_id,node_name=self.node_name,namespace=self.namespace,
            clock_subscriptions=[sub.topic_name for sub in self.node.subscriptions
                if sub.topic_name=='/navigation/control_clock'])
