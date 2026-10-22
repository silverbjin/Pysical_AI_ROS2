"""A physical-protocol wait must not occupy the clock/input executor thread."""
import threading
import time

import rclpy
import pytest
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_srvs.srv import Trigger

from integrated_robot_runtime.common import DrainingExecutor
from integrated_robot_runtime.manipulation import ManipulationNode
from integrated_robot_runtime.policy import ARM_NAMES,LEG_NAMES,STAND


def wait(predicate, timeout=3.):
    end=time.monotonic()+timeout
    while not predicate() and time.monotonic()<end:
        time.sleep(.005)
    assert predicate()


@pytest.mark.parametrize('finish',['complete','shutdown'])
def test_stow_wait_keeps_single_executor_inputs_and_clock_progressing(finish):
    rclpy.init(domain_id=149)
    node,peer=ManipulationNode(),Node('single_executor_controller_peer')
    parent,controller=SingleThreadedExecutor(),DrainingExecutor(num_threads=2)
    parent.add_node(node)
    controller.add_node(peer)
    stop,entered=threading.Event(),threading.Event()
    group=ReentrantCallbackGroup()
    pulses=[]
    node.create_timer(.02,lambda:pulses.append(time.monotonic()))
    publisher=peer.create_publisher(JointState,'/joint_states',10)

    def joints():
        msg=JointState(name=list(ARM_NAMES+LEG_NAMES),position=[0.]*6+list(STAND))
        msg.header.stamp=peer.get_clock().now().to_msg()
        publisher.publish(msg)

    peer.create_timer(.02,joints,callback_group=group)

    def execute(handle):
        entered.set()
        time.sleep(.6)
        handle.succeed()
        return FollowJointTrajectory.Result(error_code=0)

    server=ActionServer(peer,FollowJointTrajectory,
        '/arm_trajectory_controller/follow_joint_trajectory',execute,callback_group=group)
    client=peer.create_client(Trigger,'/manipulation_node/stow',callback_group=group)

    def spin(executor):
        while not stop.is_set():
            executor.spin_once(timeout_sec=.01)

    threads=[threading.Thread(target=spin,args=(e,)) for e in (parent,controller)]
    for thread in threads:
        thread.start()
    try:
        assert client.wait_for_service(timeout_sec=3)
        assert node.trajectory.wait_for_server(timeout_sec=3)
        node.on_activate(None)
        wait(lambda:node.arm is not None)
        future=client.call_async(Trigger.Request())
        assert entered.wait(timeout=3)
        before=len(pulses)
        time.sleep(.15)
        assert len(pulses)-before>=3, 'stow blocked the single clock/input executor'
        if finish=='shutdown':
            node.begin_shutdown()
        else:
            competing=client.call_async(Trigger.Request())
            wait(competing.done)
            assert not competing.result().success, 'a second protocol operation was queued'
        wait(future.done)
        if finish=='complete':
            assert future.result().success,future.result().message
            assert node.measured_safe() and node.arm_owner.pending is None
        else:
            assert not future.result().success
            wait(node.shutdown_ready)
            assert node.arm_owner.pending is None and node.protocol.idle
    finally:
        node.on_deactivate(None)
        time.sleep(.7)
        stop.set()
        for thread in threads:
            thread.join(timeout=3)
        parent.shutdown(timeout_sec=3)
        controller.shutdown(timeout_sec=3)
        node.destroy_node()
        peer.destroy_node()
        rclpy.try_shutdown()
