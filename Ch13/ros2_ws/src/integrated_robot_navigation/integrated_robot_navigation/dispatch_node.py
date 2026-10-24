"""Navigation-owned ROS entities without unused warning-only QoS waitables.

Message QoS, callbacks and ownership are unchanged. Explicit event containers
are preserved. Missing/stale inputs still fail through the measured watchdog;
default incompatible-QoS/type log warnings are not a safety acknowledgement.
Only public rclpy APIs are used; no executor or middleware internals are patched.
"""
from rclpy.event_handler import PublisherEventCallbacks, SubscriptionEventCallbacks
from rclpy.lifecycle import LifecycleNode
from rclpy.node import Node
from functools import wraps
import inspect
import hashlib
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET


def event_backend_manifest():
    """Fingerprint installed dependencies; this is file proof, not PID mapping."""
    from ament_index_python.packages import get_package_share_directory
    version=ET.parse(Path(get_package_share_directory('rclpy'))/'package.xml').getroot().findtext('version')
    report=dict(rclpy_version=version,callbacks='serial',parallel_callback_groups=False,
        reviewed_tag='7.1.12',reviewed_commit='bd637294dd02b1c128422395c059fa06df8387a3')
    for key,module in (('wrapper','rclpy.experimental.events_executor'),('extension','rclpy._rclpy_pybind11')):
        path=Path(importlib.util.find_spec(module).origin).resolve(strict=True)
        report[key]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return report


def event_compatible_callback(callback):
    """Retain MessageInfo for both Jazzy7.1.12 event and wait-set calling forms.

    The installed event loop passes the original (message, info) as one tuple;
    the regular loop unpacks it. Preserve the required signature so rclpy keeps
    requesting metadata. Never synthesize info or change the captured header.
    """
    signature=inspect.signature(callback)
    try:
        signature.bind(object())
        return callback
    except TypeError:
        signature.bind(object(),object())
    def unpack(args):
        if len(args)==1 and isinstance(args[0],tuple) and len(args[0])==2:return args[0]
        if len(args)==2:return args
        raise TypeError('expected original message and MessageInfo')
    if inspect.iscoroutinefunction(callback):
        @wraps(callback)
        async def invoke(*args):return await callback(*unpack(args))
    else:
        @wraps(callback)
        def invoke(*args):return callback(*unpack(args))
    invoke.__signature__=signature
    return invoke


class _NavigationEvents:
    def create_publisher(self,*args,**kwargs):
        if kwargs.get('event_callbacks') is None:
            kwargs['event_callbacks']=PublisherEventCallbacks(use_default_callbacks=False)
        return super().create_publisher(*args,**kwargs)

    def create_subscription(self,*args,**kwargs):
        if kwargs.get('event_callbacks') is None:
            kwargs['event_callbacks']=SubscriptionEventCallbacks(use_default_callbacks=False)
        return super().create_subscription(*args,**kwargs)


class NavigationNode(_NavigationEvents,Node):
    def create_subscription(self,msg_type,topic,callback,*args,**kwargs):
        return super().create_subscription(msg_type,topic,event_compatible_callback(callback),*args,**kwargs)


class NavigationLifecycleNode(_NavigationEvents,LifecycleNode):
    pass


def make_navigation_executor(node):
    """Upstream C++ event loop for roles that were already serial callbacks.

    EventsExecutor ignores callback-group parallelism. Never use it for crawl's
    isolated clock/sensor workers or the independent arm action receiver.
    """
    if not isinstance(node,NavigationNode):
        raise ValueError('event dispatch is restricted to ordinary navigation nodes')
    from rclpy.experimental.events_executor import EventsExecutor
    executor=EventsExecutor(context=node.context)
    if executor.context is not node.context:
        executor.shutdown()
        raise RuntimeError('navigation executor context mismatch')
    node.get_logger().info('Serial navigation callbacks use '+type(executor).__name__)
    return executor


def run_navigation_node(node_type,*,args=None):
    from integrated_robot_vision.execution import run_node
    owner=None
    def create():
        nonlocal owner
        owner=node_type()
        return owner
    run_node(create,args=args,executor_factory=lambda:make_navigation_executor(owner))
