"""Actual short ROS startup services; readiness is an observation, not a delay."""
import importlib
import time

import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from controller_manager_msgs.msg import ControllerState
from controller_manager_msgs.srv import ListControllers
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from std_srvs.srv import Trigger
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_interfaces.srv import SetMode


@pytest.mark.parametrize('case', ['delayed', 'wrong_claims', 'foreign_owner', 'carry_rejected',
                                 'bootstrap_empty', 'bootstrap_wrong_model', 'clock_arm', 'clock_arm_rejected'])
def test_startup_waits_for_measured_stand_then_carry_and_never_auto_walks(robot_model, tmp_path, case):
    assert importlib.util.find_spec('integrated_robot_navigation.startup'), 'startup sequencer missing'
    module = importlib.import_module('integrated_robot_navigation.startup')
    ctx = Context()
    rclpy.init(context=ctx)
    peer = Node('startup_service_peer', context=ctx)
    model_path = tmp_path/'robot.urdf'
    model_path.write_text(robot_model.urdf)
    relay_case = case in ('clock_arm', 'clock_arm_rejected')
    node = module.StartupManager(context=ctx, parameter_overrides=[
        Parameter('model_file', value=str(model_path)),
        Parameter('control_clock_mode', value='relay100' if relay_case else 'native'),
        Parameter('validation_mode', value=relay_case)])
    executor = SingleThreadedExecutor(context=ctx)
    executor.add_node(peer)
    executor.add_node(node)
    calls, states = [], []
    guard_mode, stand_ready, carry_ready = 'HOLD', False, False
    feedback_ready, active = False, False
    controllers_active = False

    def controllers(request, response):
        response.controller = [ControllerState(name='joint_state_broadcaster', state='active')]
        groups = {
            'leg_position_controller': [p+'_'+j+'_joint/position'
                for p in ('fr', 'fl', 'rr', 'rl') for j in ('hip', 'thigh', 'calf')],
            'arm_trajectory_controller': ['arm_joint_'+str(i)+'/position' for i in range(1, 7)],
            'gripper_position_controller': ['gripper_left_joint/position', 'gripper_right_joint/position']}
        for name, claims in groups.items():
            if case == 'wrong_claims' and name == 'arm_trajectory_controller':
                claims = claims[:-1]
            response.controller.append(ControllerState(name=name,
                state='active' if controllers_active else 'inactive',
                claimed_interfaces=claims if controllers_active else []))
        if controllers_active and case == 'foreign_owner':
            response.controller.append(ControllerState(name='foreign_arm', state='active',
                claimed_interfaces=['arm_joint_1/position']))
        return response

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
        response.success = case != 'carry_rejected'
        response.message = 'arm action server unavailable' if not response.success else 'reserved'
        return response

    def arm_clock(request, response):
        calls.append(('clock', 'arm'))
        response.success = case != 'clock_arm_rejected'
        response.message = 'clock not fresh' if not response.success else 'armed once'
        return response

    peer.create_service(SetMode, '/navigation/set_mode', mode)
    peer.create_service(ChangeState, '/crawl_controller/change_state', lifecycle)
    peer.create_service(Trigger, '/carry_manager/prepare', prepare)
    peer.create_service(ListControllers, '/controller_manager/list_controllers', controllers)
    peer.create_service(Trigger, '/navigation_control_clock/arm', arm_clock)
    pubs = {key: peer.create_publisher(MotionState, '/navigation/'+key+'_state', 10)
            for key in ('guard', 'crawl', 'carry')}
    peer.create_subscription(MotionState, '/navigation/startup_state', states.append, 10)

    def pump(seconds):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            for key, pub in pubs.items():
                msg = MotionState(generation=0, model_sha256=robot_model.model_sha256,
                    state=guard_mode if key == 'guard' else ('STAND' if active else 'INACTIVE')
                          if key == 'crawl' else 'READY',
                    phase=('BOOTSTRAP_FEEDBACK_READY' if feedback_ready else 'BOOTSTRAP_WAIT_FEEDBACK')
                          if key == 'crawl' else '',
                    ready=stand_ready if key == 'crawl' else carry_ready if key == 'carry' else False,
                    stopped=stand_ready if key == 'crawl' else False)
                if key == 'crawl' and not feedback_ready:
                    if case == 'bootstrap_empty':
                        msg.model_sha256 = ''
                    elif case == 'bootstrap_wrong_model':
                        msg.model_sha256 = '0'*64
                msg.header.stamp = peer.get_clock().now().to_msg()
                msg.header.frame_id = 'base_link'
                pub.publish(msg)
            executor.spin_once(timeout_sec=.01)

    try:
        pump(.4)
        assert calls == [('mode', 'STAND'), ('lifecycle', Transition.TRANSITION_CONFIGURE)]
        if case == 'bootstrap_wrong_model':
            assert states[-1].state == 'FAULT' and 'model mismatch' in states[-1].fault_reason
            return
        assert states[-1].state != 'FAULT', 'unconfigured empty model is waiting, not a different physical model'
        feedback_ready = True
        pump(.3)
        assert ('lifecycle', Transition.TRANSITION_ACTIVATE) not in calls, \
            'measured feedback must not substitute for active controller claims'
        assert ('carry', 'prepare') not in calls
        assert ('clock', 'arm') not in calls, 'no arming before measured feedback and real claims'
        controllers_active = True
        pump(.4)
        if case in ('wrong_claims', 'foreign_owner'):
            assert states[-1].state == 'FAULT' and not states[-1].ready
            assert 'interface' in states[-1].fault_reason
            assert ('lifecycle', Transition.TRANSITION_ACTIVATE) not in calls
            return
        if relay_case:
            assert calls.count(('clock', 'arm')) == 1, 'explicit one-shot clock arming missing'
            if case == 'clock_arm_rejected':
                assert states[-1].state == 'FAULT' and 'clock not fresh' in states[-1].fault_reason
                count = len(calls)
                pump(.3)
                assert len(calls) == count
                assert ('lifecycle', Transition.TRANSITION_ACTIVATE) not in calls
                return
            assert calls.index(('clock','arm')) < calls.index(('lifecycle',Transition.TRANSITION_ACTIVATE))
        assert calls[-1] == ('lifecycle', Transition.TRANSITION_ACTIVATE)
        stand_ready = True
        pump(.25)
        assert calls[-1] == ('carry', 'prepare') and not states[-1].ready
        if case == 'carry_rejected':
            assert states[-1].state == 'FAULT'
            assert 'arm action server unavailable' in states[-1].fault_reason
            count = len(calls)
            pump(.3)
            assert len(calls) == count, 'rejection is not an automatic retry permission'
            return
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
