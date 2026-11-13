#!/usr/bin/env python3
"""Ch06 §6.6 Gazebo-only hardware-interface acceptance, no fake controller.

Send one bounded FollowJointTrajectory to real gz_ros2_control, observe live
/clock and /joint_states, verify action SUCCESSFUL and joint movement. This
intentionally does NOT claim MoveIt planning, GUI, or physical robot success.
"""
import json
import math
import os
from pathlib import Path
import time

from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint
import rclpy

ARM = ("joint1", "joint2", "joint3", "joint4", "joint_wrist")
GOAL_TIMEOUT_S = 12.0
OBSERVATION_TIMEOUT_S = 12.0


class GazeboActionProbe(Node):
    def __init__(self):
        super().__init__("ch06_66_gazebo_action_probe")
        self.states = []
        self.clocks = []
        self.feedback = 0
        self.create_subscription(JointState, "/joint_states", self.on_joint, 30)
        self.create_subscription(Clock, "/clock", self.on_clock, 30)
        self.client = ActionClient(
            self, FollowJointTrajectory,
            "/arm_group_controller/follow_joint_trajectory",
        )

    def on_joint(self, msg):
        pos = dict(zip(msg.name, msg.position))
        if all(name in pos and math.isfinite(pos[name]) for name in ARM):
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9
            self.states.append((stamp, {k: float(pos[k]) for k in ARM}))
            if len(self.states) > 2500:
                self.states.pop(0)

    def on_clock(self, msg):
        self.clocks.append(msg.clock.sec + msg.clock.nanosec / 1e9)
        if len(self.clocks) > 2500:
            self.clocks.pop(0)

    def on_feedback(self, _message):
        self.feedback += 1


def spin_until(node, predicate, seconds, stage):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.20)
        if predicate():
            return True
    raise TimeoutError("CH06_66_TIMEOUT_" + stage)


def main():
    rclpy.init()
    probe = GazeboActionProbe()
    try:
        spin_until(
            probe, lambda: len(probe.states) >= 15 and len(probe.clocks) >= 15,
            15., "CLOCK_AND_JOINT_READY",
        )
        before = dict(probe.states[-1][1])
        if probe.clocks[-1] - probe.clocks[0] <= 0.3:
            raise RuntimeError("CH06_66_SIM_CLOCK_NOT_ADVANCING")
        start_stamp = probe.states[0][0]
        if probe.states[-1][0] <= start_stamp:
            raise RuntimeError("CH06_66_JOINT_STAMPS_NOT_ADVANCING")
        print(
            "CH06_66_SIM_CLOCK_AND_JOINT_STREAM_PASS "
            f"clock_delta_s={probe.clocks[-1]-probe.clocks[0]:.3f} "
            f"joint_samples={len(probe.states)}",
            flush=True,
        )

        if not probe.client.wait_for_server(timeout_sec=8.0):
            raise RuntimeError("CH06_66_TRAJECTORY_SERVER_MISSING")
        print("CH06_66_ACTUAL_GAZEBO_ACTION_SERVER_PASS", flush=True)

        # All positions are measured. Change just one joint at safe magnitude
        # inside its [-2.0944,+2.0944] URDF bound; no arbitrary hardware drive.
        target_joint3 = (0.45 if before["joint3"] < 0.20 else
                         max(-1.0, before["joint3"] - 0.35))
        if abs(target_joint3 - before["joint3"]) < 0.25:
            raise RuntimeError("CH06_66_GOAL_TOO_CLOSE_TO_CURRENT")
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(ARM)
        point = JointTrajectoryPoint()
        point.positions = [target_joint3 if name == "joint3" else before[name]
                           for name in ARM]
        point.time_from_start.sec = 4
        goal.trajectory.points = [point]
        # Stamp zero tells controller to start now in its own sim-time domain.
        goal.trajectory.header.stamp.sec = 0
        goal.trajectory.header.stamp.nanosec = 0

        baseline_n = len(probe.states)
        future = probe.client.send_goal_async(
            goal, feedback_callback=probe.on_feedback)
        spin_until(probe, lambda: future.done(), GOAL_TIMEOUT_S, "ACCEPT_GOAL")
        handle = future.result()
        if not handle.accepted:
            raise RuntimeError("CH06_66_GOAL_REJECTED")
        print("CH06_66_GAZEBO_GOAL_ACCEPTED", flush=True)

        result_future = handle.get_result_async()
        spin_until(probe, lambda: result_future.done(), 22., "RESULT")
        outcome = result_future.result()
        status = outcome.status
        error = outcome.result.error_code
        if status != GoalStatus.STATUS_SUCCEEDED or error != 0:
            raise RuntimeError(
                f"CH06_66_TRAJECTORY_FAILED status={status} error_code={error}"
            )
        print(
            "CH06_66_GAZEBO_FOLLOW_JOINT_TRAJECTORY_SUCCEEDED "
            f"feedback={probe.feedback}", flush=True,
        )
        spin_until(
            probe,
            lambda: (len(probe.states) > baseline_n + 10 and
                     abs(probe.states[-1][1]["joint3"] - target_joint3) < 0.08),
            OBSERVATION_TIMEOUT_S,
            "OBSERVED_JOINT_TARGET",
        )
        after = dict(probe.states[-1][1])
        measured_delta = abs(after["joint3"] - before["joint3"])
        error_joint3 = abs(after["joint3"] - target_joint3)
        observed_clock = probe.clocks[-1] - probe.clocks[0]
        if measured_delta < 0.20 or error_joint3 > 0.08 or probe.feedback < 1:
            raise RuntimeError("CH06_66_ACTUAL_JOINT_MOTION_NOT_PROVEN")
        if observed_clock < 2.0:
            raise RuntimeError("CH06_66_SIM_TIME_INSUFFICIENT")
        print(
            "CH06_66_GAZEBO_JOINT_MOTION_FEEDBACK_PASS "
            f"delta_joint3_rad={measured_delta:.6f} "
            f"goal_error_rad={error_joint3:.6f} "
            f"clock_delta_s={observed_clock:.3f} "
            f"joint_samples={len(probe.states)}",
            flush=True,
        )
        receipt = {
            "chapter": "Ch06", "section": "6.6",
            "scope": "actual_gazebo_gz_ros2_control_one_action_no_moveit_plan",
            "action": "FollowJointTrajectory",
            "goal_status": status, "error_code": error,
            "baseline_joint3_rad": before["joint3"],
            "command_joint3_rad": target_joint3,
            "observed_joint3_rad": after["joint3"],
            "observed_joint_movement_rad": measured_delta,
            "target_error_rad": error_joint3,
            "clock_advanced_s": observed_clock,
            "joint_samples": len(probe.states),
            "action_feedback_count": probe.feedback,
            "sim_urdf_plugin": "REQUIRES_INDEPENDENT_CI_PROOF",
            "moveit_planning": "NOT_RUN",
            "gazebo_gui": "NOT_RUN",
            "real_hardware": "NOT_RUN",
            "gripper": "NOT_RUN",
            "ch10": "HOLD",
        }
        path = Path(os.environ["CH06_66_RECEIPT"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(receipt, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        print("CH06_66_CONTROLLER_GAZEBO_SCOPE_PASS_MOVEIT_PLANNING_NOT_RUN",
              flush=True)
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(
            f"CH06_66_FAIL type={type(exc).__name__} reason={exc}",
            flush=True,
        )
        return 1
    finally:
        probe.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
