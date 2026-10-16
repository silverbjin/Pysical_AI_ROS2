#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node

from tf2_ros import Buffer
from tf2_ros import TransformListener

from sensor_msgs.msg import JointState

from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup

import time

class MoveItDiagnostic(Node):

    def __init__(self):
        super().__init__("moveit_diagnostic")

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(
            self.tf_buffer,
            self
        )
        self.latest_joint_state = None

        self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_callback,
            10
        )
        self.move_group_client = ActionClient(
            self,
            MoveGroup,
            "/move_action"
        )

    def joint_callback(self, msg):
        self.latest_joint_state = msg

    def check_joint_states(self):

        print("\n========== JOINT STATES ==========")

        if self.latest_joint_state is None:
            print("[FAIL] no /joint_states received")
            return False

        js = self.latest_joint_state

        print(f"[INFO] joints = {len(js.name)}")

        if len(js.name) == 0:
            print("[FAIL] empty JointState")
            return False

        if len(js.name) != len(js.position):
            print("[FAIL] name/position mismatch")
            return False

        print("[PASS] joint_states OK")

        for name, pos in zip(js.name, js.position):
            print(f"  {name:20s} {pos:.3f}")

        return True

    def check_move_group(self):

        print("\n========== MOVE GROUP ==========")

        if self.move_group_client.wait_for_server(
            timeout_sec=2.0
        ):
            print("[PASS] MoveGroup server found")
            return True

        print("[FAIL] MoveGroup server missing")
        return False

    # def check_tf(self):
    #     print("\n========== TF ==========")
    #     try:
    #         tf = self.tf_buffer.lookup_transform(
    #             "base_link",
    #             "target_object",
    #             rclpy.time.Time()
    #         )
    #         x = tf.transform.translation.x
    #         y = tf.transform.translation.y
    #         z = tf.transform.translation.z

    #         dist = math.sqrt(
    #             x*x + y*y + z*z
    #         )
    #         print(
    #             f"[INFO] target_object = "
    #             f"({x:.3f}, {y:.3f}, {z:.3f})"
    #         )
    #         print(
    #             f"[INFO] distance = {dist:.3f} m"
    #         )

    #         if dist > 0.6:
    #             print(
    #                 "[WARN] target may be outside arm workspace"
    #             )
    #     except Exception as e:
    #         print(
    #             f"[FAIL] TF lookup failed: {e}"
    #         )

    # def check_tf(self):
    #     print("\n========== TF ==========")
    #     for _ in range(20):
    #         rclpy.spin_once(
    #             self,
    #             timeout_sec=0.2
    #         )
    #         try:
    #             frames = self.tf_buffer.all_frames_as_yaml()
    #             if "base_link" in frames:
    #                 break
    #         except:
    #             pass
    #     print(frames)

    #     try:
    #         tf = self.tf_buffer.lookup_transform(
    #             "base_link",
    #             "target_object",
    #             rclpy.time.Time()
    #         )
    #         x = tf.transform.translation.x
    #         y = tf.transform.translation.y
    #         z = tf.transform.translation.z
    #         print(
    #             f"[PASS] TF found "
    #             f"({x:.3f}, {y:.3f}, {z:.3f})"
    #         )

    #     except Exception as e:
    #         print(
    #             f"[FAIL] TF lookup failed: {e}"
    #         )
                                
    # def check_tf(self):
    #     print("\n========== TF ==========")
    #     frames = ""
    #     for _ in range(20):
    #         rclpy.spin_once(
    #             self,
    #             timeout_sec=0.2
    #         )
    #         try:
    #             frames = self.tf_buffer.all_frames_as_yaml()
    #             if "base_link" in frames:
    #                 break
    #         except Exception:
    #             pass
    #     print(frames)

    #     try:
    #         tf = self.tf_buffer.lookup_transform(
    #             "base_link",
    #             "target_object",
    #             rclpy.time.Time()
    #         )
    #         x = tf.transform.translation.x
    #         y = tf.transform.translation.y
    #         z = tf.transform.translation.z

    #         # -----------------------------
    #         # 거리 계산
    #         # -----------------------------
    #         horizontal_dist = math.sqrt(
    #             x * x + y * y
    #         )

    #         distance_3d = math.sqrt(
    #             x * x +
    #             y * y +
    #             z * z
    #         )
    #         print(
    #             f"[PASS] TF found "
    #             f"({x:.3f}, {y:.3f}, {z:.3f})"
    #         )
    #         print(
    #             f"[INFO] Horizontal distance = "
    #             f"{horizontal_dist:.3f} m"
    #         )
    #         print(
    #             f"[INFO] Height (z) = "
    #             f"{z:.3f} m"
    #         )
    #         print(
    #             f"[INFO] 3D distance = "
    #             f"{distance_3d:.3f} m"
    #         )

    #         # -----------------------------
    #         # Workspace 진단
    #         # -----------------------------
    #         SAFE_REACH = 0.50
    #         if distance_3d > SAFE_REACH:
    #             print(
    #                 "[WARN] Target may be outside workspace"
    #             )
    #             print(
    #                 f"[WARN] distance "
    #                 f"({distance_3d:.3f} m) "
    #                 f"> SAFE_REACH ({SAFE_REACH:.3f} m)"
    #             )
    #         else:
    #             print(
    #                 "[PASS] Target appears "
    #                 "inside workspace"
    #             )
    #     except Exception as e:
    #         print(
    #             f"[FAIL] TF lookup failed: {e}"
    #         )

    def check_tf(self):
        print("\n========== TF ==========")
        frames = ""
        for _ in range(20):
            rclpy.spin_once(
                self,
                timeout_sec=0.2
            )
            try:
                frames = self.tf_buffer.all_frames_as_yaml()
                if "base_link" in frames:
                    break
            except Exception:
                pass
        print(frames)
        try:
            # -------------------------------------------------
            # Target Object TF
            # -------------------------------------------------
            target_tf = self.tf_buffer.lookup_transform(
                "base_link",
                "target_object",
                rclpy.time.Time()
            )
            tx = target_tf.transform.translation.x
            ty = target_tf.transform.translation.y
            tz = target_tf.transform.translation.z
            horizontal_dist = math.sqrt(
                tx * tx +
                ty * ty
            )
            target_dist = math.sqrt(
                tx * tx +
                ty * ty +
                tz * tz
            )
            print(
                f"[PASS] Target TF found "
                f"({tx:.3f}, {ty:.3f}, {tz:.3f})"
            )
            print(
                f"[INFO] Horizontal distance = "
                f"{horizontal_dist:.3f} m"
            )
            print(
                f"[INFO] Height (z) = "
                f"{tz:.3f} m"
            )
            print(
                f"[INFO] 3D distance = "
                f"{target_dist:.3f} m"
            )
            # -------------------------------------------------
            # End Effector TF
            # -------------------------------------------------
            ee_tf = self.tf_buffer.lookup_transform(
                "base_link",
                "link_wrist",
                rclpy.time.Time()
            )
            ex = ee_tf.transform.translation.x
            ey = ee_tf.transform.translation.y
            ez = ee_tf.transform.translation.z
            print(
                f"[INFO] End-Effector Position = "
                f"({ex:.3f}, {ey:.3f}, {ez:.3f})"
            )
            # -------------------------------------------------
            # EE -> Target 거리
            # -------------------------------------------------
            ee_target_dist = math.sqrt(
                (tx - ex) ** 2 +
                (ty - ey) ** 2 +
                (tz - ez) ** 2
            )
            print(
                f"[INFO] EE -> Target distance = "
                f"{ee_target_dist:.3f} m"
            )
            # -------------------------------------------------
            # Workspace 진단
            # -------------------------------------------------
            SAFE_REACH = 0.50
            if target_dist > SAFE_REACH:
                print(
                    "[WARN] Target may be outside workspace"
                )
                print(
                    f"[WARN] distance "
                    f"({target_dist:.3f} m) "
                    f"> SAFE_REACH ({SAFE_REACH:.3f} m)"
                )
            else:
                print(
                    "[PASS] Target appears inside workspace"
                )
            # -------------------------------------------------
            # 추가 해석
            # -------------------------------------------------
            if ee_target_dist > SAFE_REACH:
                print(
                    "[WARN] End-Effector is very far "
                    "from target position"
                )
        except Exception as e:
            print(
                f"[FAIL] TF lookup failed: {e}"
            )

    def run(self):
        self.check_joint_states()
        self.check_move_group()
        self.check_tf()

def main():
    rclpy.init()
    node = MoveItDiagnostic()
    print("waiting for ROS graph...")

    start = time.time()
    while time.time() - start < 5.0:

        rclpy.spin_once(
            node,
            timeout_sec=0.1
        )

    node.run()

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()
