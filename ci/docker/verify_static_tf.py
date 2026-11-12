#!/usr/bin/env python3
"""Verify a real transient-local static TF message from the Ch04 book node.

The test does not treat publisher logging alone as proof that a subscriber
received the transform. All discovered TF messages are evaluated.
"""
import math
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from tf2_msgs.msg import TFMessage


def main():
    rclpy.init()
    node = Node("book_ch04_static_tf_probe")
    observed = []
    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
    )
    node.create_subscription(TFMessage, "/tf_static",
                             lambda msg: observed.extend(msg.transforms), qos)
    deadline = time.monotonic() + 15.0
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.3)
            for t in observed:
                if (t.header.frame_id == "base_link" and
                        t.child_frame_id == "lidar_sensor_link"):
                    p = t.transform.translation
                    q = t.transform.rotation
                    assert math.isclose(p.x, 0.1, abs_tol=1e-5), "wrong x"
                    assert math.isclose(p.y, 0.0, abs_tol=1e-5), "wrong y"
                    assert math.isclose(p.z, 0.2, abs_tol=1e-5), "wrong z"
                    assert math.isclose(q.w, 1.0, abs_tol=1e-5), "wrong rotation"
                    print("CH04_TF_STATIC_QOS_RECEIVED_PASS parent=base_link child=lidar_sensor_link", flush=True)
                    return 0
        print("CH04_TF_STATIC_RECEIVE_FAIL: no expected transform in 15s; received=" +
              str([(t.header.frame_id, t.child_frame_id) for t in observed]), file=sys.stderr)
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
