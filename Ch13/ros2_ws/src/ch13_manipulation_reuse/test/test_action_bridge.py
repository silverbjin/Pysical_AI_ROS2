import threading
import time
from types import SimpleNamespace
import pytest
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.action import GoalResponse
from control_msgs.action import FollowJointTrajectory,GripperCommand
from trajectory_msgs.msg import JointTrajectoryPoint
from ch13_manipulation_reuse.action_bridge import ActionBridge
from ch13_manipulation_reuse.lease import Lease


@pytest.fixture
def bridge():
    rclpy.init(args=[],domain_id=136)
    node=Node('test_manipulation_action_boundary')
    node.lock=threading.RLock()
    executor=SingleThreadedExecutor();executor.add_node(node)
    extension=SimpleNamespace(node=node,lease=Lease('engine'),events=[])
    result=ActionBridge(extension)
    yield result
    result.close();executor.remove_node(node);executor.shutdown();node.destroy_node();rclpy.shutdown()


def admit(bridge,request):
    executor=bridge.node.executor
    future=executor.create_task(bridge.arm_goal,request)
    executor.spin_until_future_complete(future,timeout_sec=3.)
    assert future.done()
    return future.result()


def goal():
    request=FollowJointTrajectory.Goal()
    request.trajectory.joint_names=['joint'+str(i) for i in range(1,7)]
    for t in [0,2]:
        p=JointTrajectoryPoint();p.time_from_start.sec=t;p.positions=[.0]*6
        request.trajectory.points.append(p)
    return request


def test_action_requires_live_lease_and_actual_measured_state(bridge):
    assert admit(bridge,goal())==GoalResponse.REJECT
    bridge.extension.lease.phase='READY'
    assert admit(bridge,goal())==GoalResponse.REJECT


def test_duplicate_goals_and_nonfinite_gripper_rejected(bridge):
    bridge.extension.lease.phase='READY'
    bridge.measured=[0.]*6
    bridge.limits=[(-2.,2.)]*6
    assert admit(bridge,goal())==GoalResponse.ACCEPT
    assert admit(bridge,goal())==GoalResponse.REJECT
    g=GripperCommand.Goal();g.command.position=float('nan')
    assert bridge.gripper_goal(g)==GoalResponse.REJECT


def test_effort_cap_and_joint7_stroke_are_enforced(bridge):
    bridge.extension.lease.phase='READY';bridge.measured=[0.]*6
    for position,effort in [(.06,.5),(.01,.51),(-.001,.2),(.02,float('nan'))]:
        request=GripperCommand.Goal();request.command.position=position;request.command.max_effort=effort
        assert bridge.gripper_goal(request)==GoalResponse.REJECT


def test_validation_does_not_block_receipts_or_hold_physics_lock(bridge):
    bridge.extension.lease.phase='READY';bridge.measured=[0.]*6;bridge.limits=[(-2.,2.)]*6
    original=bridge.validate_request
    def delayed(*args):
        time.sleep(.08)
        return original(*args)
    bridge.validate_request=delayed
    receipts=[]
    def receipt():
        with bridge.node.lock:receipts.append(time.monotonic())
    timer=bridge.node.create_timer(.01,receipt)
    request=goal();request.trajectory.header.frame_id='reuse/odom'
    assert admit(bridge,request)==GoalResponse.ACCEPT
    assert len(receipts)>=3
    bridge.node.destroy_timer(timer)
