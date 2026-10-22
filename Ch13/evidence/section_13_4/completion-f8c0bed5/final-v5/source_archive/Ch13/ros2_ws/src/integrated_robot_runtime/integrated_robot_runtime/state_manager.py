"""Bounded lifecycle startup, measured arm gate, and rollback on any failure."""
import json
import time
import signal
import threading

import rclpy
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.signals import SignalHandlerOptions
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import String
from std_srvs.srv import Trigger
from controller_manager_msgs.srv import ListControllers


class StateManager(Node):
    def __init__(self):
        super().__init__('state_manager')
        self.declare_parameter('operation_timeout', 15.0)
        self.declare_parameter('wait_for_controllers', False)
        self.events = []
        self.stopping = threading.Event()
        self.service_clients = {}
        self.publisher = self.create_publisher(
            String, '/architecture/startup',
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))

    def call(self, kind, path, request):
        timeout = float(self.get_parameter('operation_timeout').value)
        if path not in self.service_clients:
            self.service_clients[path] = self.create_client(kind, path)
        client = self.service_clients[path]
        if not client.wait_for_service(timeout_sec=timeout):
            raise TimeoutError(f'{path} unavailable')
        future = client.call_async(request)
        deadline = time.monotonic() + timeout
        while not future.done() and not self.stopping.is_set() and time.monotonic() < deadline:
            self.executor.spin_once(timeout_sec=0.1)
        if not future.done():
            raise TimeoutError(f'{path} timed out or shutdown requested')
        return future.result()

    def transition(self, node, transition):
        request = ChangeState.Request()
        request.transition.id = transition
        if not self.call(ChangeState, f'/{node}/change_state', request).success:
            raise RuntimeError(f'{node} rejected lifecycle transition {transition}')

    def wait_controllers(self, timeout=60.):
        client = self.create_client(ListControllers, '/controller_manager/list_controllers')
        deadline = time.monotonic()+timeout
        names = ('joint_state_broadcaster', 'leg_position_controller',
                 'arm_trajectory_controller', 'gripper_position_controller')
        try:
            while time.monotonic() < deadline and not self.stopping.is_set():
                if not client.wait_for_service(timeout_sec=.1):
                    continue
                future = client.call_async(ListControllers.Request())
                while not future.done() and time.monotonic() < deadline and not self.stopping.is_set():
                    self.executor.spin_once(timeout_sec=.05)
                if future.done():
                    states = {v.name: v.state for v in future.result().controller}
                    if all(states.get(name) == 'active' for name in names):
                        return
                next_poll = min(deadline, time.monotonic()+.1)
                while time.monotonic() < next_poll and not self.stopping.is_set():
                    self.executor.spin_once(timeout_sec=.02)
            raise TimeoutError('native engine controllers not all active before deadline')
        finally:
            self.destroy_client(client)

    def startup(self):
        started = time.monotonic()
        active = []
        result = {'status': 'FAILED'}
        try:
            if self.get_parameter('wait_for_controllers').value:
                self.wait_controllers()
            for node, event in (('manipulation_node', 'arm_configured'),
                                ('locomotion_node', 'legs_configured')):
                self.transition(node, Transition.TRANSITION_CONFIGURE)
                self.events.append(event)
            self.transition('manipulation_node', Transition.TRANSITION_ACTIVATE)
            active.append('manipulation_node')
            self.events.append('arm_active')
            response = self.call(Trigger, '/manipulation_node/stow', Trigger.Request())
            if not response.success:
                raise RuntimeError(response.message)
            self.events.append('arm_safe')
            self.transition('locomotion_node', Transition.TRANSITION_ACTIVATE)
            active.append('locomotion_node')
            self.events.append('legs_active')
            result['status'] = 'READY'
        except Exception as exc:
            result['error'] = str(exc)
            for node in reversed(active):
                try:
                    self.transition(node, Transition.TRANSITION_DEACTIVATE)
                except Exception as rollback_error:
                    result.setdefault('rollback_errors', []).append(str(rollback_error))
        result.update(events=list(self.events), elapsed_s=time.monotonic() - started)
        self.publisher.publish(String(data=json.dumps(result)))
        self.get_logger().info(json.dumps(result))


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = StateManager()
    signal.signal(signal.SIGINT, lambda *_: node.stopping.set())
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        node.startup()
        while rclpy.ok() and not node.stopping.is_set():
            executor.spin_once(timeout_sec=0.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
