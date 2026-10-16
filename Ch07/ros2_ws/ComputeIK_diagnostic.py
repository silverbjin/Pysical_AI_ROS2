#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from moveit_msgs.srv import GetPositionIK
from moveit_msgs.msg import PositionIKRequest
from geometry_msgs.msg import PoseStamped


class IKTester(Node):
    def __init__(self):
        super().__init__("ik_tester")
        self.client = self.create_client(GetPositionIK, "/compute_ik")
        while not self.client.wait_for_service(timeout_sec=1.0):
            print("waiting for /compute_ik ...")

    def test_pose(self, x, y, z):
        req = GetPositionIK.Request()
        ik = PositionIKRequest()
        ik.group_name = "arm_group"
        ik.robot_state.joint_state.name = [
            "joint1", "joint2","joint3", "joint4", "joint_wrist"
        ]
        ik.robot_state.joint_state.position = [
            0.0, 0.0, 1.57, 0.0, 0.0
        ]
        ik.pose_stamped = PoseStamped()
        ik.pose_stamped.header.frame_id = "base_link"
        ik.pose_stamped.pose.position.x = x
        ik.pose_stamped.pose.position.y = y
        ik.pose_stamped.pose.position.z = z

        # ik.pose_stamped.pose.orientation.w = 1.0
        ik.pose_stamped.pose.orientation.x = -0.674506
        ik.pose_stamped.pose.orientation.y = 0.677911
        ik.pose_stamped.pose.orientation.z = -0.206224
        ik.pose_stamped.pose.orientation.w = 0.207243
        ik.timeout.sec = 2
        req.ik_request = ik
        future = self.client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        result = future.result()

        print("\n======================")
        print(f"Target = ({x:.3f}, {y:.3f}, {z:.3f})")
        print(
            f"ErrorCode = "
            f"{result.error_code.val}"
        )
        if result.error_code.val == 1:
            print("\n[PASS] IK FOUND")
            js = result.solution.joint_state
            for n, p in zip(js.name, js.position):
                print(f"{n:20s}" f"{p:.4f}")
        else:
            print("\n[FAIL] IK FAILED")

def main():
    rclpy.init()
    node = IKTester()
    node.test_pose(0.9083, 0.00, 0.1289)
    node.test_pose(0.30, 0.00, 0.30)
    node.test_pose(0.40, 0.00, 0.40)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()