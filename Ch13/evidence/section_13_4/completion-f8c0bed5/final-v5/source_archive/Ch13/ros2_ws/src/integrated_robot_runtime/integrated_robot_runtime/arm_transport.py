"""Low-traffic action receiver, independent of the robot callback worker pool.

This owns communication resources only. ArmActionOwner remains the sole command
lease owner; neither executor shutdown nor a cancel ACK releases that lease.
"""
import threading

from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node


class ArmActionTransport:
    def __init__(self, parent):
        # Do not inherit wildcard use_sim_time or launch __node remappings:
        # action RPCs need no /clock subscription or simulated-time timer.
        self.node = Node(parent.get_name() + '_arm_transport',
                         context=parent.context, namespace=parent.get_namespace(),
                         use_global_arguments=False)
        self.executor = SingleThreadedExecutor(context=parent.context)
        self.executor.add_node(self.node)
        self.client = ActionClient(self.node, FollowJointTrajectory,
            parent.resolve_topic_name('/arm_trajectory_controller/follow_joint_trajectory'))
        self.stop = threading.Event()
        self.error = None
        self.closed = False
        self.thread = threading.Thread(target=self._run, name='ch13-arm-action-receiver')

    @property
    def healthy(self):
        return self.thread.is_alive() and not self.stop.is_set() and self.error is None

    def start(self):
        self.thread.start()

    def _run(self):
        try:
            while not self.stop.is_set() and self.node.context.ok():
                self.executor.spin_once(timeout_sec=.02)
        except ExternalShutdownException as exc:
            if not self.stop.is_set():
                self.error = exc
        except Exception as exc:
            self.error = exc
            self.node.get_logger().error('Arm action receiver stopped: ' + repr(exc))

    def close(self):
        if self.closed:
            return
        self.stop.set()
        self.executor.wake()
        if self.thread.ident is not None:
            self.thread.join(timeout=2.)
        if self.thread.is_alive():
            # Never destroy ROS handles while their owning callback is running.
            raise RuntimeError('Arm action receiver did not stop; ROS resources retained')
        self.executor.shutdown(timeout_sec=2.)
        self.client.destroy()
        self.node.destroy_node()
        self.closed = True
