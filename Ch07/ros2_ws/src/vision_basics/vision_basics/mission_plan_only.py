#!/usr/bin/env python3
"""Ch07 §7.7 E2: real RGB-D target -> collision-aware MoveIt PLAN ONLY.

Reads ONLY the existing G01 /ch07_77/target_ready. Never sends arm or
finger FollowJointTrajectory / MoveIt execute. Default observe-only mode.
Test-only 24mm rod fixture geometry is not a production grasp calibration.
"""
import json
import math
import os
from pathlib import Path
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PointStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from .mission_geometry import ARM, fixture_plan_targets

ALLOWED_MODES = ("observe", "plan_only")


class SensorPlanOnly(Node):
    def __init__(self):
        super().__init__("ch07_77_sensor_moveit_plan_only")
        self.declare_parameter("mode", "observe")
        self.declare_parameter("target_timeout_sec", 25.0)
        mode = str(self.get_parameter("mode").value)
        if mode not in ALLOWED_MODES:
            raise ValueError("CH07_E2_FORBIDDEN_EXECUTE_MODE")
        self.mode = mode
        self.received = None
        self.target = None
        self.plan_client = (ActionClient(self, MoveGroup, "/move_action")
                            if mode == "plan_only" else None)
        self.create_subscription(PointStamped, "/ch07_77/target_ready",
                                 self.on_target, 10)
        self.report = {
            "scope": "CH07_77_E2_SENSOR_TARGET_TO_MOVEIT_PLAN_ONLY",
            "mode": mode,
            "status": "NOT_RUN",
            "source_sha": os.environ.get("RUN_SOURCE_SHA", "UNKNOWN"),
            "sensor_target_provenance": "G01_STAMPED_TARGET_READY",
            "move_group_plan_only_requests": 0,
            "arm_motor_goal_count": 0,
            "gripper_motor_goal_count": 0,
            "actual_physical_grasp": "NOT_RUN",
            "G04B_PHYSICAL_CLEAN": "BLOCKED",
            "G05_FULL_E2E": "NOT_RUN",
            "Ch10": "HOLD",
            "stages": []
        }
        self.get_logger().warn(
            "CH07_E2_SENSOR_TO_PLAN_ONLY_NO_MOTOR_GOALS mode=" + mode)

    def on_target(self, msg):
        if self.received is not None:
            self.get_logger().warn("CH07_E2_DUPLICATE_TARGET_IGNORED")
            return
        self.received = msg
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        now = self.get_clock().now().nanoseconds * 1e-9
        xyz = (msg.point.x, msg.point.y, msg.point.z)
        self.report["target"] = {
            "stamp_sec": stamp, "frame": msg.header.frame_id,
            "xyz_m": list(xyz), "observed_sim_sec": now
        }
        if msg.header.frame_id != "base_link":
            self.report["reason"] = "WRONG_TARGET_FRAME"
            return
        if not all(math.isfinite(x) for x in (*xyz, stamp, now)):
            self.report["reason"] = "NONFINITE_SENSOR_TARGET"
            return
        if stamp <= 0 or now <= 0 or not (-0.1 <= now - stamp <= 0.8):
            self.report["reason"] = "STALE_TARGET"
            return
        try:
            self.target = fixture_plan_targets(xyz)
            self.report["candidates"] = [
                {"stage": t["stage"], "wrist_xyz_m": list(t["wrist_xyz_m"]),
                 "joints_rad": dict(t["joints_rad"])}
                for t in self.target
            ]
            self.report["target_admission"] = "VALID_FOR_PLAN_ONLY"
        except ValueError as exc:
            self.report["reason"] = str(exc)
            self.get_logger().warn("CH07_E2_TARGET_REJECTED " + str(exc))

    def await_future(self, future, timeout_sec, description):
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if future.done():
                return future.result()
        raise TimeoutError("CH07_E2_TIMEOUT_" + description)

    def do_plan(self, candidate):
        name = candidate["stage"]
        joints = candidate["joints_rad"]
        if self.plan_client is None or not self.plan_client.wait_for_server(timeout_sec=8.0):
            raise RuntimeError("CH07_E2_MOVEGROUP_NOT_READY")
        goal = MoveGroup.Goal()
        goal.request.group_name = "arm_group"
        goal.request.allowed_planning_time = 6.0
        goal.request.num_planning_attempts = 2
        goal.request.max_velocity_scaling_factor = 0.15
        goal.request.max_acceleration_scaling_factor = 0.15
        goal.request.start_state.is_diff = True
        goal.planning_options.plan_only = True
        goal.planning_options.replan = False
        goal.planning_options.planning_scene_diff.is_diff = True
        constraints = Constraints()
        for joint_name in ARM:
            joint = JointConstraint()
            joint.joint_name = joint_name
            joint.position = float(joints[joint_name])
            joint.tolerance_above = joint.tolerance_below = 0.035
            joint.weight = 1.0
            constraints.joint_constraints.append(joint)
        goal.request.goal_constraints.append(constraints)
        self.report["move_group_plan_only_requests"] += 1
        handle = self.await_future(
            self.plan_client.send_goal_async(goal), 12.0, name + "_ACCEPT")
        if handle is None or not handle.accepted:
            raise RuntimeError("CH07_E2_MOVEGROUP_REJECTED_" + name)
        try:
            result = self.await_future(
                handle.get_result_async(), 45.0, name + "_PLAN")
        except TimeoutError:
            self.await_future(handle.cancel_goal_async(), 5.0, name + "_CANCEL")
            raise
        info = {
            "stage": name,
            "sensor_based_wrist_xyz_m": list(candidate["wrist_xyz_m"]),
            "joint_request": joints,
            "goal_status": int(result.status),
            "moveit_error_code": int(result.result.error_code.val),
            "planned_points": len(
                result.result.planned_trajectory.joint_trajectory.points),
            "plan_only": True,
        }
        self.report["stages"].append(info)
        if (info["goal_status"] != GoalStatus.STATUS_SUCCEEDED or
                info["moveit_error_code"] != MoveItErrorCodes.SUCCESS or
                info["planned_points"] < 1):
            raise RuntimeError("CH07_E2_MOVEGROUP_PLAN_FAIL_" + name)
        self.get_logger().info("CH07_E2_PLAN_ONLY_SUCCESS " + name)
        return info


def main(args=None):
    rclpy.init(args=args)
    node = None
    report = None
    failed = False
    try:
        node = SensorPlanOnly()
        report = node.report
        deadline = time.monotonic() + float(
            node.get_parameter("target_timeout_sec").value)
        while rclpy.ok() and time.monotonic() < deadline and node.received is None:
            rclpy.spin_once(node, timeout_sec=0.1)
        if node.received is None:
            raise RuntimeError("CH07_E2_NO_LIVE_SENSOR_TARGET")
        if node.target is None:
            raise RuntimeError("CH07_E2_TARGET_REJECTED_" + report.get("reason", ""))
        if node.mode == "observe":
            report["status"] = "SENSOR_TARGET_OBSERVED_NO_GOAL"
        else:
            for candidate in node.target:
                node.do_plan(candidate)
            report["status"] = "SENSOR_TO_MOVEIT_PLAN_ONLY_PASS"
        print("CH07_E2_" + report["status"], flush=True)
    except (KeyboardInterrupt, ExternalShutdownException) as exc:
        failed = True
        if report is not None:
            report["reason"] = "SHUTDOWN_OR_INTERRUPTED"
        print("CH07_E2_INTERRUPTED " + str(exc), flush=True)
    except Exception as exc:
        failed = True
        if report is not None:
            report["reason"] = repr(exc)
        print("CH07_E2_FAIL " + repr(exc), flush=True)
    finally:
        if report is not None:
            path = Path(os.environ.get("CH07_77_E2_RECEIPT",
                                       "/tmp/ch07_77_e2_receipt.json"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
