#!/usr/bin/env python3
"""Ch07 #173 G01 entrypoint: real ROS target admission only, **zero Goals**.

This replaces the broken legacy target_object-TF polling and constant xyz
motion path. G02: actual RGB-D calibration; G03: MoveIt plan/execute;
G04: physical contact/lift/place. These stages are NOT implemented here.
"""
import math

import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import Bool

from .mission_target_gate import TargetGate, candidate_pregrasp


class MissionController(Node):
    def __init__(self):
        super().__init__("mission_controller")
        self.declare_parameter("max_age_s", 0.8)
        self.declare_parameter("pregrasp_z_m", 0.12)
        self.declare_parameter("surface_to_center_z_m", 0.0)
        self.gate = TargetGate(max_age_s=float(self.get_parameter("max_age_s").value))
        self.pub = self.create_publisher(PointStamped, "/ch07_77/target_ready", 10)
        self.pose_pub = self.create_publisher(PoseStamped, "/ch07_77/pregrasp_candidate", 10)
        self.create_subscription(Bool, "/camera/target_valid", self.on_valid, 10)
        self.create_subscription(PointStamped, "/camera/target_3d_base", self.on_target, 10)
        self.get_logger().warn(
            "CH07_77_G01_ADMISSION_ONLY_NO_MOVEIT_NO_GRIPPER_NO_GOAL; "
            "target is a surface point, not an approved grasp pose")

    def now_s(self):
        return self.get_clock().now().nanoseconds / 1e9

    def on_valid(self, msg):
        self.gate.set_valid(msg.data, self.now_s())

    def on_target(self, msg):
        t = self.gate.accept(
            xyz=(msg.point.x, msg.point.y, msg.point.z),
            stamp_s=msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            frame_id=msg.header.frame_id, now_s=self.now_s())
        if t is None:
            self.get_logger().info("CH07_77_G01_REJECT_OR_HOLD reason=%s" % self.gate.last_reason)
            return
        # G01 only; never plan or actuate. Proposed geometry not yet calibrated.
        xyz = candidate_pregrasp(
            t,
            surface_to_center_z_m=float(
                self.get_parameter("surface_to_center_z_m").value),
            pregrasp_z_m=float(self.get_parameter("pregrasp_z_m").value))
        ready = PointStamped()
        ready.header = msg.header
        ready.point.x, ready.point.y, ready.point.z = t.x, t.y, t.z
        self.pub.publish(ready)
        pose = PoseStamped()
        pose.header = msg.header
        pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = xyz
        # Identity is a placeholder for an UNPLANNED candidate, never an IK
        # or a validated grasp orientation. G03 will use robot-specific IK.
        pose.pose.orientation.w = 1.0
        self.pose_pub.publish(pose)
        self.get_logger().warn(
            "CH07_77_G01_REAL_ROS_STABLE_TARGET_READY_NO_GOAL "
            "stamp=%.6f xyz=(%.6f,%.6f,%.6f) candidate=(%.6f,%.6f,%.6f)"
            % (t.stamp_s, t.x, t.y, t.z, *xyz))


def main(args=None):
    rclpy.init(args=args)
    node = MissionController()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        # Jazzy SIGTERM may shut the rcl context down while executor waits.
        # This is a normal owned-process teardown, not an unhandled crash.
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
