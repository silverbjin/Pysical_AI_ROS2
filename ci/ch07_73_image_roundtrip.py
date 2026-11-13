#!/usr/bin/env python3
"""True ROS 2 Image → vision_basics.vision_processor → mono8 ROS Image audit.

The input image is synthetic, NOT a Gazebo camera frame. Verify the actual
ROS DDS pub/sub path, CvBridge, OpenCV/Canny pixels, encoding and exact stamp.
Preserve Ch07 §7.2 real-camera renderer BLOCKED state.
"""
import json
import os
from pathlib import Path
import time

import cv2
import numpy as np
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image


class Fixture(Node):
    def __init__(self):
        super().__init__("book_ch07_73_synthetic_fixture")
        qos=QoSProfile(depth=10,history=HistoryPolicy.KEEP_LAST,
                       reliability=ReliabilityPolicy.BEST_EFFORT)
        self.publisher=self.create_publisher(Image,"/camera/image_raw",qos)
        self.messages=[]
        self.subscription=self.create_subscription(
            Image,"/camera/processed_image",self.receive,10)

    def receive(self,msg):
        self.messages.append(msg)


def main():
    rclpy.init()
    node=Fixture()
    try:
        source=np.zeros((48,64,3),dtype=np.uint8)
        source[10:35,15:47]=(0,0,255)
        bridge=CvBridge()
        original=bridge.cv2_to_imgmsg(source,encoding="bgr8")
        original.header.frame_id="camera_optical_frame"
        original.header.stamp.sec=271828
        original.header.stamp.nanosec=182845904
        grayscale=cv2.cvtColor(source,cv2.COLOR_BGR2GRAY)
        expected=cv2.Canny(cv2.GaussianBlur(grayscale,(5,5),0),50,150)
        if not expected.any():
            raise RuntimeError("CH07_73_BAD_FIXTURE_NO_EDGES")
        deadline=time.monotonic()+16
        sent=0
        while time.monotonic()<deadline and len(node.messages)<3:
            node.publisher.publish(original)
            sent+=1
            rclpy.spin_once(node,timeout_sec=0.13)
        if len(node.messages)<3:
            raise RuntimeError(
                f"CH07_73_NO_REAL_PROCESSED_TOPIC samples={len(node.messages)} "
                f"sent={sent}")
        for i,msg in enumerate(node.messages[:3]):
            if msg.encoding!="mono8" or msg.width!=64 or msg.height!=48:
                raise RuntimeError(f"CH07_73_BAD_ENCODING_OR_SHAPE sample={i}")
            if (msg.header.stamp.sec != 271828
                    or msg.header.stamp.nanosec!=182845904
                    or msg.header.frame_id!="camera_optical_frame"):
                raise RuntimeError(f"CH07_73_HEADER_NOT_PRESERVED sample={i}")
            received=bridge.imgmsg_to_cv2(msg,desired_encoding="mono8")
            if received.dtype!=np.uint8 or not np.array_equal(received,expected):
                raise RuntimeError(f"CH07_73_EDGE_PIXELS_INCORRECT sample={i}")
        evidence={
            "chapter":"Ch07","section":"7.3",
            "scenario":"synthetic_ROS_image_cv_bridge_OpenCV_Canny_mono8",
            "status":"SCOPED_PASS",
            "input_encoding":"bgr8","output_encoding":"mono8",
            "size":[64,48],
            "input_messages_published":sent,
            "real_processed_messages_verified":3,
            "edge_nonzero_pixels":int(np.count_nonzero(expected)),
            "exact_pixels_matched":True,
            "frame_id":"camera_optical_frame",
            "exact_header_stamp_preserved":True,
            "actual_gazebo_camera":"BLOCKED_ISSUE_127",
            "real_depth":"NOT_RUN",
            "opencv_gui":"NOT_RUN",
            "real_hardware":"NOT_RUN",
            "ch10":"HOLD",
        }
        out=Path(os.environ["CH07_73_RECEIPT"])
        out.parent.mkdir(parents=True,exist_ok=True)
        temp=out.with_suffix(".tmp")
        temp.write_text(json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
        os.replace(temp,out)
        print(
            "CH07_73_ACTUAL_ROS_IMAGE_CVBRIDGE_CANNY_MONO8_AND_STAMP_PASS "
            f"processed_samples=3 edges={evidence['edge_nonzero_pixels']}",
            flush=True)
        return 0
    except (Exception,KeyboardInterrupt) as exc:
        print(f"CH07_73_FAIL type={type(exc).__name__} reason={exc}",
              flush=True)
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=="__main__":
    raise SystemExit(main())
