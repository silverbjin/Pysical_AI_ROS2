#!/usr/bin/env python3
"""Ch07 real image, camera info and optical TF subscriber proof, not GUI."""
import json
import math
from pathlib import Path
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import Image, CameraInfo
from tf2_msgs.msg import TFMessage

out = Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)
rclpy.init()
node = Node("book_ch07_camera_probe")
images, infos, optical = [], [], []
sensor_qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                        reliability=ReliabilityPolicy.BEST_EFFORT)
static_qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                        reliability=ReliabilityPolicy.RELIABLE,
                        durability=DurabilityPolicy.TRANSIENT_LOCAL)

def on_image(msg):
    if msg.width and msg.height and len(msg.data) >= msg.step * msg.height:
        images.append({"width":msg.width,"height":msg.height,"encoding":msg.encoding,
                       "frame":msg.header.frame_id,"data_bytes":len(msg.data),
                       "stamp":msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec})

def on_info(msg):
    if msg.width and msg.height and math.isfinite(msg.k[0]) and msg.k[0] > 0 and msg.k[4] > 0:
        infos.append({"width":msg.width,"height":msg.height,"fx":msg.k[0],"fy":msg.k[4],
                      "frame":msg.header.frame_id})

def on_tf(msg):
    for t in msg.transforms:
        if t.header.frame_id == "camera_link" and t.child_frame_id == "camera_optical_frame":
            optical.append({"parent":t.header.frame_id,"child":t.child_frame_id})

subscriptions = [
    node.create_subscription(Image, "/camera/image_raw", on_image, sensor_qos),
    node.create_subscription(CameraInfo, "/camera/camera_info", on_info, sensor_qos),
    node.create_subscription(TFMessage, "/tf_static", on_tf, static_qos),
]
start = time.monotonic()
try:
    while time.monotonic() - start < 25:
        rclpy.spin_once(node, timeout_sec=.3)
        if len(images) >= 3 and len(infos) >= 1 and optical:
            break
    status = "PASS" if len(images) >= 3 and len(infos) >= 1 and optical else "FAIL"
    result = {"scope":"Ch07 RGB-D camera ROS Image/CameraInfo plus fixed optical TF",
              "status":status, "image_samples":len(images), "camera_info_samples":len(infos),
              "optical_tf_samples":len(optical),"example_image":images[0] if images else None,
              "example_intrinsics":infos[0] if infos else None,
              "not_run":["depth alignment", "image processing and object detection",
                         "Gazebo/RViz GUI","gripper pick and place"]}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("BOOK_CH07_CAMERA_"+status+" "+json.dumps(result),flush=True)
    sys.exit(0 if status=="PASS" else 1)
finally:
    node.destroy_node()
    if rclpy.ok(): rclpy.shutdown()
