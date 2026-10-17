#!/usr/bin/env python3
import argparse
import asyncio
import json
import math
from pathlib import Path
import subprocess
import time

import rclpy
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint


EXPECTED = {
    *(f"{leg}_{joint}_joint" for leg in ("fr", "fl", "rr", "rl") for joint in ("hip", "thigh", "calf")),
    *(f"arm_joint_{index}" for index in range(1, 7)),
    "gripper_left_joint",
    "gripper_right_joint",
}


class Probe(Node):
    def __init__(self):
        super().__init__("section_13_2_gazebo_probe")
        self.last_joint_state = None
        self.create_subscription(JointState, "/joint_states", self._on_joint_state, 10)
        self.list_client = self.create_client(ListControllers, "/controller_manager/list_controllers")
        self.arm_client = ActionClient(
            self, FollowJointTrajectory, "/arm_trajectory_controller/follow_joint_trajectory"
        )

    def _on_joint_state(self, message):
        self.last_joint_state = message


def spin_until(node, predicate, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if predicate():
            return True
    return False


def collect_joint_state(node, timeout=30.0):
    if not spin_until(node, lambda: node.last_joint_state is not None, timeout):
        raise TimeoutError("/joint_states was not received")
    message = node.last_joint_state
    values = dict(zip(message.name, message.position))
    if not EXPECTED <= values.keys() or not all(math.isfinite(values[name]) for name in EXPECTED):
        raise RuntimeError("JointState does not contain 20 finite contract joints")
    return values


def list_controllers(node, timeout=30.0):
    if not node.list_client.wait_for_service(timeout_sec=timeout):
        raise TimeoutError("controller_manager list service unavailable")
    future = node.list_client.call_async(ListControllers.Request())
    if not spin_until(node, future.done, timeout):
        raise TimeoutError("controller list timed out")
    return {item.name: item.state for item in future.result().controller}


def send_arm_goal(node, current, timeout=20.0):
    if not node.arm_client.wait_for_server(timeout_sec=timeout):
        raise TimeoutError("arm trajectory action unavailable")
    goal = FollowJointTrajectory.Goal()
    goal.trajectory.joint_names = [f"arm_joint_{index}" for index in range(1, 7)]
    point = JointTrajectoryPoint()
    point.positions = [current[name] + (0.08 if name == "arm_joint_2" else 0.0) for name in goal.trajectory.joint_names]
    point.time_from_start.sec = 2
    goal.trajectory.points = [point]
    send_future = node.arm_client.send_goal_async(goal)
    if not spin_until(node, send_future.done, timeout):
        raise TimeoutError("arm goal acceptance timed out")
    handle = send_future.result()
    if not handle.accepted:
        raise RuntimeError("arm trajectory goal rejected")
    result_future = handle.get_result_async()
    if not spin_until(node, result_future.done, timeout):
        raise TimeoutError("arm trajectory result timed out")
    return point.positions


def gazebo_pose():
    completed = subprocess.run(
        ["gz", "model", "-m", "integrated_robot", "-p"], capture_output=True, text=True, timeout=10
    )
    return {"exit_code": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}


def write_result(path, result):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rclpy.init()
    node = Probe()
    result = {"engine": "gazebo", "status": "FAIL"}
    try:
        before = collect_joint_state(node)
        controllers = list_controllers(node)
        required = {"joint_state_broadcaster", "leg_position_controller", "arm_trajectory_controller", "gripper_position_controller"}
        if any(controllers.get(name) != "active" for name in required):
            raise RuntimeError(f"controllers not active: {controllers}")
        target = send_arm_goal(node, before)
        spin_until(node, lambda: abs(dict(zip(node.last_joint_state.name, node.last_joint_state.position)).get("arm_joint_2", 0) - target[1]) < 0.04, 15.0)
        after = collect_joint_state(node)
        response = abs(after["arm_joint_2"] - before["arm_joint_2"])
        if response < 0.04:
            raise RuntimeError(f"arm_joint_2 response too small: {response}")
        result.update(status="PASS", joint_count=20, controllers=controllers, arm_joint_2_delta=response, model_pose=gazebo_pose())
    except Exception as exc:
        result["error"] = str(exc)
        raise
    finally:
        write_result(args.output, result)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
