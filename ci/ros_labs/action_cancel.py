#!/usr/bin/env python3
"""Ch02 LAB 2.6: actual Action Cancel -> STATUS_CANCELED, not Ctrl+C."""
import rclpy
from action_msgs.msg import GoalStatus
from rclpy.action import ActionClient
from rclpy.node import Node
from my_robot_interfaces.action import CountUntil

rclpy.init()
node = Node("book_lab_cancel_client")
try:
    client = ActionClient(node, CountUntil, "/count_until")
    assert client.wait_for_server(timeout_sec=8.0), "server missing"
    goal = CountUntil.Goal(target_number=20, period=0.5)
    future = client.send_goal_async(goal)
    rclpy.spin_until_future_complete(node, future, timeout_sec=8.0)
    assert future.done(), "send_goal timed out"
    handle = future.result()
    assert handle is not None and handle.accepted, "goal not accepted"
    cancel = handle.cancel_goal_async()
    rclpy.spin_until_future_complete(node, cancel, timeout_sec=8.0)
    assert cancel.done() and cancel.result().goals_canceling, "cancel not accepted"
    result = handle.get_result_async()
    rclpy.spin_until_future_complete(node, result, timeout_sec=8.0)
    assert result.done(), "get_result timed out"
    answer = result.result()
    assert answer.status == GoalStatus.STATUS_CANCELED, "final state is not CANCELED: " + str(answer.status)
    assert 0 <= answer.result.reached_number < 20, "cancel happened after completion"
    print("CH02_2_6_STATUS_CANCELED_PASS count=" + str(answer.result.reached_number), flush=True)
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
