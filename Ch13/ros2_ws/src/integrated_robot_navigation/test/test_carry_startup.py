"""Actual short ROS startup services; readiness is an observation, not a delay."""
import importlib
import time

import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from std_srvs.srv import Trigger
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_interfaces.srv import SetMode


def test_startup_waits_for_measured_stand_then_carry_and_never_auto_walks():
    assert importlib.util.find_spec('integrated_robot_navigation.startup'), 'startup sequencer missing'
    module = importlib.import_module('integrated_robot_navigation.startup')
    ctx = Context()
    rclpy.init(context=ctx)
    peer = Node('startup_service_peer', context=ctx)
    node = module.StartupManager(context=ctx)
    executor = SingleThreadedExecutor(context=ctx)
    executor.add_node(peer)
    executor.add_node(node)
    calls, states = [], []
    guard_mode, stand_ready, carry_ready = 'HOLD', False, False
    feedback_ready, active = False, False

    def mode(request, response):
        nonlocal guard_mode
        calls.append(('mode', request.mode))
        guard_mode = request.mode
        response.accepted = True
        return response

    def lifecycle(request, response):
        nonlocal active
        calls.append(('lifecycle', request.transition.id))
        response.success = request.transition.id != Transition.TRANSITION_ACTIVATE or feedback_ready
        if response.success and request.transition.id == Transition.TRANSITION_ACTIVATE:
            active = True
        return response

    def prepare(request, response):
        calls.append(('carry', 'prepare'))
        response.success = True
        return response

    peer.create_service(SetMode, '/navigation/set_mode', mode)
    peer.create_service(ChangeState, '/crawl_controller/change_state', lifecycle)
    peer.create_service(Trigger, '/carry_manager/prepare', prepare)
    pubs = {key: peer.create_publisher(MotionState, '/navigation/'+key+'_state', 10)
            for key in ('guard', 'crawl', 'carry')}
    peer.create_subscription(MotionState, '/navigation/startup_state', states.append, 10)

    def pump(seconds):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            for key, pub in pubs.items():
                msg = MotionState(generation=0, model_sha256='a'*64,
                    state=guard_mode if key == 'guard' else ('STAND' if active else 'INACTIVE')
                          if key == 'crawl' else 'READY',
                    phase='BOOTSTRAP_FEEDBACK_READY' if key == 'crawl' and feedback_ready else '',
                    ready=stand_ready if key == 'crawl' else carry_ready if key == 'carry' else False,
                    stopped=stand_ready if key == 'crawl' else False)
                msg.header.stamp = peer.get_clock().now().to_msg()
                msg.header.frame_id = 'base_link'
                pub.publish(msg)
            executor.spin_once(timeout_sec=.01)

    try:
        pump(.4)
        assert calls == [('mode', 'STAND'), ('lifecycle', Transition.TRANSITION_CONFIGURE)]
        feedback_ready = True
        pump(.2)
        assert calls[-1] == ('lifecycle', Transition.TRANSITION_ACTIVATE)
        stand_ready = True
        pump(.25)
        assert calls[-1] == ('carry', 'prepare') and not states[-1].ready
        carry_ready = True
        pump(.25)
        assert states[-1].ready and states[-1].state == 'READY'
        count = len(calls)
        pump(.2)
        assert len(calls) == count and ('mode', 'CRAWL') not in calls
    finally:
        executor.shutdown(timeout_sec=2.)
        node.destroy_node()
        peer.destroy_node()
        ctx.try_shutdown()
