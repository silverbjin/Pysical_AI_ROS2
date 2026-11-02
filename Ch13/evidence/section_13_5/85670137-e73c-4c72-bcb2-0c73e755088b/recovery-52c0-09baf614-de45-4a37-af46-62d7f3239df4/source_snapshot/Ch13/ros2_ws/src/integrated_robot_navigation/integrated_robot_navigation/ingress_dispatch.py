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
from .dispatch_node import event_compatible_callback, event_backend_manifest


class _IngressNode(Node):
    def create_subscription(self,msg_type,topic,callback,*args,**kwargs):
        # The two installed executors present MessageInfo differently. Keep the
        # same original message/info and required signature for both forms.
        return super().create_subscription(msg_type,topic,
            event_compatible_callback(callback),*args,**kwargs)


class IngressDispatch:
    def __init__(self,context,name,namespace,subscriptions,*,autostart=True):
        self.error=None
        self.joined=False
        self.stopping=threading.Event()
        self.node=_IngressNode(name,context=context,namespace=namespace,
            use_global_arguments=False,start_parameter_services=False,enable_rosout=False)
        self.node_name=self.node.get_name()
        self.namespace=self.node.get_namespace()
        self.executor=SingleThreadedExecutor(context=context)
        self.backend='waitset'
        self.backend_manifest=None
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

    def select_backend(self,backend):
        """Select only before the one owned serial receiver starts.

        No live switch/restart, model callbacks, services or action execution
        are introduced. The normal backend remains the original wait-set.
        """
        if self.thread.ident is not None or self.joined:
            raise RuntimeError('ingress already started; backend cannot change')
        if backend not in ('waitset','events'):raise ValueError('unknown ingress backend')
        if backend==self.backend:return
        manifest=None
        if backend=='events':
            from rclpy.experimental.events_executor import EventsExecutor
            manifest=event_backend_manifest()
            replacement=EventsExecutor(context=self.node.context)
        else:replacement=SingleThreadedExecutor(context=self.node.context)
        try:
            self.executor.remove_node(self.node)
            if not self.executor.shutdown(timeout_sec=2.):
                raise RuntimeError('previous ingress executor shutdown unconfirmed')
            replacement.add_node(self.node)
        except BaseException:
            replacement.shutdown(timeout_sec=2.)
            raise
        self.executor=replacement
        self.backend,self.backend_manifest=backend,manifest

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
        return dict(dispatch='owned_serial_'+self.backend,alive=self.thread.is_alive(),
            joined=self.joined,error=self.error,pid=os.getpid(),uid=os.getuid(),
            native_tid=self.thread.native_id,node_name=self.node_name,namespace=self.namespace,
            executor_type=type(self.executor).__name__,backend_manifest=self.backend_manifest,
            clock_subscriptions=[sub.topic_name for sub in self.node.subscriptions
                if sub.topic_name=='/navigation/control_clock'])
