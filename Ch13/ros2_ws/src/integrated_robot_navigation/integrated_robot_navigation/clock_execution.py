"""Opt-in TimeSource dispatch isolation; never replace or duplicate its clock.

Only public Node subscription/remap and executor APIs are used. The existing
rclpy TimeSource still owns the one ROS clock subscription and clock updates.
"""
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from rclpy.lifecycle import LifecycleNode
from rosgraph_msgs.msg import Clock


class ControlClockLifecycleNode(LifecycleNode):
    def __init__(self,*args,**kwargs):
        # TimeSource subscribes during Node construction; the group must exist
        # before super().__init__. Native /clock is left in the original group.
        self.navigation_clock_group = MutuallyExclusiveCallbackGroup()
        super().__init__(*args,**kwargs)

    def create_subscription(self,msg_type,topic,callback,qos_profile,*,callback_group=None,**kwargs):
        if (msg_type is Clock and callback_group is None
                and self.resolve_topic_name(topic) == '/navigation/control_clock'):
            callback_group = self.navigation_clock_group
        return super().create_subscription(msg_type,topic,callback,qos_profile,
            callback_group=callback_group,**kwargs)


def make_control_executor(node):
    mode = node.get_parameter('control_clock_mode').value
    if mode == 'native':
        return SingleThreadedExecutor(context=node.context)
    if mode != 'relay100' or node.get_parameter('validation_mode').value is not True:
        raise ValueError('control_clock isolated executor requires validation_mode')
    return MultiThreadedExecutor(num_threads=2,context=node.context)


def run_control_node(node_type,*,args=None):
    # Reuse the established deferred-SIGINT/resource-join owner. No copied or
    # edited 13.4 implementation, no constructor-time background executor.
    from integrated_robot_vision.execution import run_node
    owner = None
    def create():
        nonlocal owner
        owner = node_type()
        return owner
    run_node(create,args=args,executor_factory=lambda: make_control_executor(owner))
