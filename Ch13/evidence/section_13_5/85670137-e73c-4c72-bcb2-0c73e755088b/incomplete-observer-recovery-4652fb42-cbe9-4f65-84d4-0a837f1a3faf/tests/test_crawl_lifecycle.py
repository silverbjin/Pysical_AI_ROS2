"""Actual lifecycle services and owned publication; no physical engine."""
import importlib
import time

import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from std_msgs.msg import Float64MultiArray
from geometry_msgs.msg import Twist
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_navigation.carry_profile import prepare_profile
from guard_fixture import CARRY
from test_motion_guard_ros import Rig


class CrawlRig(Rig):
    def __init__(self, controller, model, context):
        from integrated_robot_navigation.clock_execution import make_control_executor
        super().__init__(controller, model, context, executor_factory=make_control_executor)
        self.node.destroy_publisher(self.leg)  # the actual crawl node is the sole leg publisher
        self.gate = self.node.create_publisher(MotionState, '/navigation/guard_state', 10)
        self.final = self.node.create_publisher(Twist, '/navigation/cmd_vel', 10)
        self.mode_name, self.value = 'STAND', 0.
        self.ready = False  # bootstrap must not depend on completed carry
        self.gate_delay_ns = 0  # test-source delay, never a production clock change
        self.commands, self.crawl_states = [], []
        self.leg_sub = self.node.create_subscription(Float64MultiArray,
            '/leg_position_controller/commands', self.commands.append, 10)
        self.crawl_sub = self.node.create_subscription(MotionState,
            '/navigation/crawl_state', self.crawl_states.append, 10)
        self.lifecycle = self.node.create_client(ChangeState, '/crawl_controller/change_state')

    def pump(self, duration, **kwargs):
        from builtin_interfaces.msg import Time
        end = time.monotonic()+duration
        while time.monotonic() < end:
            sec = int(self.capture)
            message = MotionState(generation=self.generation, model_sha256=self.model.model_sha256,
                                  state=self.mode_name, ready=self.mode_name == 'CRAWL')
            message.header.stamp = Time(sec=sec, nanosec=int((self.capture-sec)*1e9))
            if self.gate_delay_ns:
                delayed = int(self.capture*1e9)-self.gate_delay_ns
                message.header.stamp = Time(sec=delayed//1_000_000_000, nanosec=delayed%1_000_000_000)
            message.header.frame_id = 'nav_base'
            self.gate.publish(message)
            velocity = Twist()
            velocity.linear.x = self.value
            self.final.publish(velocity)
            super().pump(.02, **kwargs)

    def transition(self, identifier):
        assert self.lifecycle.wait_for_service(timeout_sec=1.)
        request = ChangeState.Request(transition=Transition(id=identifier))
        future = self.lifecycle.call_async(request)
        deadline = time.monotonic()+2.
        while not future.done() and time.monotonic() < deadline:
            self.pump(.02)
        assert future.done(), 'lifecycle deadline'
        return future.result().success


@pytest.fixture
def crawl_rig(nav_robot_model, request):
    module = importlib.import_module('integrated_robot_navigation.crawl_controller') if importlib.util.find_spec(
        'integrated_robot_navigation.crawl_controller') else None
    assert module is not None, 'crawl lifecycle owner missing'
    profile = prepare_profile(nav_robot_model, CARRY)
    ctx = Context()
    rclpy.init(context=ctx)
    controller = module.CrawlController(nav_robot_model, profile, 'mujoco', context=ctx,
        parameter_overrides=[Parameter('use_sim_time', value=True),
                             Parameter('validation_mode', value=getattr(request, 'param', False))])
    value = CrawlRig(controller, nav_robot_model, ctx)
    try:
        value.pump(.3)
        yield value
    finally:
        value.close()
        ctx.try_shutdown()


def test_lifecycle_inactive_cannot_command_then_bootstrap_stand_without_carry(crawl_rig):
    rig = crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    rig.pump(.1)
    assert not rig.commands
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(.15)
    assert rig.commands and all(len(msg.data) == 12 for msg in rig.commands)
    assert rig.node.count_publishers('/leg_position_controller/commands') == 1
    assert rig.transition(Transition.TRANSITION_DEACTIVATE)
    rig.pump(.05)
    count = len(rig.commands)
    rig.pump(.15)
    assert len(rig.commands) == count


def test_inactive_bootstrap_feedback_signal_is_fresh_and_never_commands(crawl_rig):
    rig = crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    rig.pump(.1)
    assert rig.crawl_states[-1].phase == 'BOOTSTRAP_FEEDBACK_READY'
    assert not rig.crawl_states[-1].ready and not rig.commands
    rig.pump(.28, clock=False)
    assert rig.crawl_states[-1].phase == 'BOOTSTRAP_WAIT_FEEDBACK'
    assert not rig.crawl_states[-1].ready and not rig.commands


def test_unvalidated_profile_cannot_walk_even_with_external_ready_flag(crawl_rig):
    rig = crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(.1)
    rig.mode_name, rig.value, rig.ready = 'CRAWL', .001, True
    rig.pump(.15)
    assert rig.crawl_states[-1].state == 'FAULT'
    assert 'native_validation_required' in rig.crawl_states[-1].fault_reason
    count = len(rig.commands)
    rig.mode_name, rig.value = 'STAND', 0.
    rig.pump(.15)
    assert len(rig.commands) == count, 'recovered input must not auto-rearm'


def test_activation_without_native_feedback_is_rejected(nav_robot_model):
    module = importlib.import_module('integrated_robot_navigation.crawl_controller') if importlib.util.find_spec(
        'integrated_robot_navigation.crawl_controller') else None
    assert module is not None, 'crawl lifecycle owner missing'
    ctx = Context()
    rclpy.init(context=ctx)
    controller = module.CrawlController(nav_robot_model, prepare_profile(nav_robot_model, CARRY),
        'mujoco', context=ctx, parameter_overrides=[Parameter('use_sim_time', value=True)])
    peer = Node('empty_feedback_lifecycle_test', context=ctx)
    executor = SingleThreadedExecutor(context=ctx)
    executor.add_node(controller)
    executor.add_node(peer)
    client = peer.create_client(ChangeState, '/crawl_controller/change_state')
    try:
        assert client.wait_for_service(timeout_sec=1.)
        for identifier, expected in ((Transition.TRANSITION_CONFIGURE, True),
                                     (Transition.TRANSITION_ACTIVATE, False)):
            future = client.call_async(ChangeState.Request(transition=Transition(id=identifier)))
            executor.spin_until_future_complete(future, timeout_sec=2.)
            assert future.done() and future.result().success is expected
    finally:
        executor.shutdown(timeout_sec=2.)
        controller.destroy_node()
        peer.destroy_node()
        ctx.try_shutdown()
