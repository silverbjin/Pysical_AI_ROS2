#!/usr/bin/env python3
"""Ch07 §7.6: execute sequential open/close goals on two prismatic joints.

Simulation only. Report goal accepted, result status/error and measured
/joint_states separately. This does NOT imply a physical object was grasped.
"""
import math
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from sensor_msgs.msg import JointState

FINGERS = ("joint_finger1", "joint_finger2")
OPEN_M = 0.005
CLOSE_M = 0.020
LIMIT_MIN_M = 0.0
LIMIT_MAX_M = 0.025
GOAL_ERROR_M = 0.003


class GripperController(Node):
    def __init__(self):
        super().__init__("gripper_controller")
        self.client = ActionClient(
            self, FollowJointTrajectory,
            "/gripper_group_controller/follow_joint_trajectory")
        self.measurements = []
        self.create_subscription(JointState, "/joint_states", self.on_state, 10)

    def on_state(self, msg):
        positions = dict(zip(msg.name, msg.position))
        if all(name in positions and math.isfinite(positions[name])
               for name in FINGERS):
            self.measurements.append({n:float(positions[n]) for n in FINGERS})
            if len(self.measurements) > 2000:
                self.measurements.pop(0)

    def until(self, condition, timeout, stage):
        stop = time.monotonic() + timeout
        while time.monotonic() < stop:
            rclpy.spin_once(self, timeout_sec=0.10)
            if condition():
                return
        raise TimeoutError(f"CH07_76_TIMEOUT_{stage}")

    def move_gripper(self, position, label):
        """Wait for real action result before sending another goal."""
        if not (LIMIT_MIN_M <= position <= LIMIT_MAX_M):
            raise ValueError("CH07_76_GOAL_OUTSIDE_URDF_PRISMATIC_LIMITS")
        if not self.client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError("CH07_76_FOLLOW_JOINT_TRAJECTORY_SERVER_MISSING")
        self.until(lambda:bool(self.measurements), 10, "FIRST_JOINT_STATE")
        start = dict(self.measurements[-1])
        count = len(self.measurements)
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(FINGERS)
        point = JointTrajectoryPoint()
        point.positions = [position, position]
        point.time_from_start.sec = 2
        goal.trajectory.points = [point]
        result_future = self.client.send_goal_async(goal)
        self.until(result_future.done, 10, f"{label}_ACCEPTANCE")
        handle = result_future.result()
        if handle is None or not handle.accepted:
            raise RuntimeError(f"CH07_76_{label}_GOAL_REJECTED")
        completed_future = handle.get_result_async()
        self.until(completed_future.done, 12, f"{label}_RESULT")
        outcome = completed_future.result()
        status = outcome.status
        error_code = outcome.result.error_code
        if status != GoalStatus.STATUS_SUCCEEDED or error_code != 0:
            raise RuntimeError(
                f"CH07_76_{label}_ACTION_FAILED status={status} error_code={error_code}"
            )
        self.until(
            lambda:(len(self.measurements)>count+3
                    and all(abs(self.measurements[-1][n]-position)<=GOAL_ERROR_M
                            for n in FINGERS)),
            8, f"{label}_JOINT_FEEDBACK",
        )
        measured = dict(self.measurements[-1])
        error=max(abs(measured[n]-position) for n in FINGERS)
        delta=max(abs(measured[n]-start[n]) for n in FINGERS)
        print(
            f"CH07_76_{label}_ACTION_AND_MEASURED_JOINTS_PASS "
            f"goal_m={position:.5f} max_error_m={error:.6f} "
            f"max_joint_change_m={delta:.6f} "
            f"joint1_m={measured[FINGERS[0]]:.6f} "
            f"joint2_m={measured[FINGERS[1]]:.6f}",
            flush=True,
        )
        return {"action":"SUCCEEDED","goal_m":position,
                "max_error_m":error,"max_joint_change_m":delta,
                "joints_m":measured}

    def run_demo(self):
        self.until(lambda:bool(self.measurements),15,"ACTUAL_JOINT_STATE_READY")
        print("CH07_76_REAL_JOINT_STATE_STREAM_READY", flush=True)
        open_result = self.move_gripper(OPEN_M,"OPEN")
        close_result = self.move_gripper(CLOSE_M,"CLOSE")
        if close_result["max_joint_change_m"] < 0.010:
            raise RuntimeError("CH07_76_INSUFFICIENT_FINGER_MOTION")
        print("CH07_76_SEQUENCE_OPEN_RESULT_THEN_CLOSE_REAL_FEEDBACK_PASS",
              flush=True)
        return {"open":open_result,"close":close_result,
                "units":"m", "two_prismatic_joints":list(FINGERS),
                "actual_object_grasp":"NOT_RUN"}


def main(args=None):
    rclpy.init(args=args)
    node=GripperController()
    try:
        node.run_demo()
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(f"CH07_76_FAIL type={type(exc).__name__} reason={exc}",
              file=sys.stderr,flush=True)
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__=="__main__":
    raise SystemExit(main())
