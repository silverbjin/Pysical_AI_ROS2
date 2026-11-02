"""Opt-in TimeSource dispatch isolation; never replace or duplicate its clock.

Node subscription/remap uses public APIs. The existing runtime DrainingExecutor
owns the localized Jazzy shutdown compatibility hook. The rclpy TimeSource
still owns the one ROS clock subscription and clock updates.
"""
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import SingleThreadedExecutor
from integrated_robot_runtime.common import DrainingExecutor
from .dispatch_node import NavigationLifecycleNode as LifecycleNode
from rosgraph_msgs.msg import Clock


class ControlClockLifecycleNode(LifecycleNode):
    def __init__(self,*args,**kwargs):
        # TimeSource subscribes during Node construction. Its receiver is built
        # but not started here. Native /clock remains on the original node.
        self.navigation_clock_group = MutuallyExclusiveCallbackGroup()
        self.navigation_clock_dispatch = None
        self.navigation_clock_subscriptions = set()
        try:
            super().__init__(*args,**kwargs)
        except BaseException:
            if self.navigation_clock_dispatch is not None:self.navigation_clock_dispatch.close()
            raise

    def create_subscription(self,msg_type,topic,callback,qos_profile,*,callback_group=None,**kwargs):
        if (msg_type is Clock and callback_group is None
                and self.resolve_topic_name(topic) == '/navigation/control_clock'):
            # TimeSource retains its original callback and ROSClock. Its public
            # subscription owner isolates dispatch; notifications follow the
            # original callback. There is no duplicate /clock,
            # clock forwarding, private TimeSource patch or timestamp rewrite.
            if self.navigation_clock_dispatch is None:
                from .ingress_dispatch import IngressDispatch
                self.navigation_clock_dispatch = IngressDispatch(self.context,
                    self.get_name()+'_ingress',self.get_namespace(),[],autostart=False)
            def original_clock_then_notify(message):
                callback(message)
                # Notify only after the original TimeSource updates its clock.
                # No extra subscription, clock value or model mutation here.
                notify=getattr(self,'_notify_reference_dispatch',None)
                if notify is not None:notify()
            subscription=self.navigation_clock_dispatch.node.create_subscription(
                msg_type,self.resolve_topic_name(topic),original_clock_then_notify,qos_profile,**kwargs)
            self.navigation_clock_subscriptions.add(subscription)
            return subscription
        return super().create_subscription(msg_type,topic,callback,qos_profile,
            callback_group=callback_group,**kwargs)

    def destroy_subscription(self,subscription):
        if subscription in self.navigation_clock_subscriptions:
            self.navigation_clock_subscriptions.remove(subscription)
            if self.navigation_clock_dispatch.joined:return True
            return self.navigation_clock_dispatch.node.destroy_subscription(subscription)
        return super().destroy_subscription(subscription)

    def destroy_node(self):
        if self.navigation_clock_dispatch is not None:self.navigation_clock_dispatch.close()
        return super().destroy_node()


def make_control_executor(node):
    mode = node.get_parameter('control_clock_mode').value
    if mode == 'native':
        return SingleThreadedExecutor(context=node.context)
    if mode != 'relay100' or node.get_parameter('validation_mode').value is not True:
        raise ValueError('control_clock isolated executor requires validation_mode')
    if getattr(node,'direct_model_dispatch',False) or getattr(node,'simulation_cadence',False):
        # The validation model group is serial already; TimeSource and ingress
        # have their own receiver. Dispatch the sole owner directly instead of
        # handing each decision through another Python callback worker queue.
        node.get_logger().info('Validation model uses direct serial dispatch with isolated ingress')
        return SingleThreadedExecutor(context=node.context)
    return DrainingExecutor(num_threads=2,context=node.context)


def run_control_node(node_type,*,args=None):
    # Reuse deferred-SIGINT/resource-join ownership. Crawl starts its receiver
    # only after construction is complete; TimeSource registration starts none.
    from integrated_robot_vision.execution import run_node
    owner = None
    def create():
        nonlocal owner
        owner = node_type()
        return owner
    run_node(create,args=args,executor_factory=lambda: make_control_executor(owner))
