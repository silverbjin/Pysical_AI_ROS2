#!/usr/bin/env python3
"""Actual ROS red-object detector regression on synthetic Images, not camera.

Tests one/two/no objects with real ROS pub/sub. For each nonempty frame verify
PointStamped pixel center and AREA (point.z is NOT depth). For blank input
require explicit /camera/target_valid false to avoid stale target reuse.
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
from geometry_msgs.msg import PointStamped
from std_msgs.msg import Bool


class Fixture(Node):
    def __init__(self):
        super().__init__("book_ch07_74_red_fixture")
        qos=QoSProfile(depth=10,history=HistoryPolicy.KEEP_LAST,
                       reliability=ReliabilityPolicy.BEST_EFFORT)
        self.publisher=self.create_publisher(Image,"/camera/image_raw",qos)
        self.target=[]
        self.valid=[]
        self.images=[]
        self.create_subscription(PointStamped,"/camera/target_pixel",
                                 lambda x:self.target.append(x),10)
        self.create_subscription(Bool,"/camera/target_valid",
                                 lambda x:self.valid.append(x.data),10)
        self.create_subscription(Image,"/camera/detection_result",
                                 lambda x:self.images.append(x),10)

    def send_and_check(self,source,stamp,expected_center):
        bridge=CvBridge()
        msg=bridge.cv2_to_imgmsg(source,encoding="bgr8")
        msg.header.frame_id="camera_optical_frame"
        msg.header.stamp.sec=stamp
        baseline_valid=len(self.valid)
        started=time.monotonic()
        while time.monotonic()-started<8:
            self.publisher.publish(msg)
            rclpy.spin_once(self,timeout_sec=0.10)
            got_image=any(x.header.stamp.sec==stamp and
                          x.header.frame_id=="camera_optical_frame"
                          and x.encoding=="bgr8" for x in self.images)
            if not got_image or len(self.valid)==baseline_valid:
                continue
            if expected_center is None:
                if self.valid[-1] is not False:
                    continue
                # Allow DDS callbacks from earlier input to drain before
                # asserting that *this timestamp* has no published target.
                end=time.monotonic()+0.35
                while time.monotonic()<end:
                    rclpy.spin_once(self,timeout_sec=0.05)
                if any(x.header.stamp.sec==stamp for x in self.target):
                    raise RuntimeError("CH07_74_STALE_COORD_AFTER_BLANK")
                print("CH07_74_CASE_3_EMPTY_INVALIDATION_PASS",flush=True)
                return {"status":"EMPTY_INVALIDATED","target_count":0}
            for target in self.target:
                if target.header.stamp.sec!=stamp:
                    continue
                if not self.valid[-1]:
                    continue
                if (abs(target.point.x-expected_center[0])>2
                        or abs(target.point.y-expected_center[1])>2):
                    raise RuntimeError(
                        f"CH07_74_WRONG_CENTER stamp={stamp} "
                        f"point=({target.point.x},{target.point.y})")
                if target.point.z <= 500:
                    raise RuntimeError("CH07_74_TARGET_AREA_TOO_SMALL")
                return {"status":"VALID","cx":target.point.x,
                        "cy":target.point.y,"area_px2":target.point.z,
                        "stamp":stamp}
        raise TimeoutError(f"CH07_74_CASE_TIMEOUT stamp={stamp} "
                           f"img={len(self.images)} valid={len(self.valid)} "
                           f"target={len(self.target)}")


def main():
    rclpy.init()
    node=Fixture()
    try:
        one=np.zeros((240,320,3),dtype=np.uint8)
        cv2.rectangle(one,(100,70),(180,150),(0,0,255),-1)
        a=node.send_and_check(one,101,(140,110))
        print(f"CH07_74_CASE_1_RED_VALID_PASS area_px2={a['area_px2']}",
              flush=True)

        two=np.zeros((240,320,3),dtype=np.uint8)
        cv2.rectangle(two,(30,40),(60,70),(0,0,255),-1)
        cv2.rectangle(two,(190,120),(260,200),(0,0,255),-1)
        b=node.send_and_check(two,102,(225,160))
        if b["area_px2"]<=a["area_px2"]*0.5:
            raise RuntimeError("CH07_74_LARGEST_CONTOUR_CONTRACT_INCONSISTENT")
        print(f"CH07_74_CASE_2_MAX_CONTOUR_PASS area_px2={b['area_px2']}",
              flush=True)

        blank=np.zeros((240,320,3),dtype=np.uint8)
        c=node.send_and_check(blank,103,None)
        data={
            "chapter":"Ch07","section":"7.4","status":"SCOPED_PASS",
            "fixture":"three_synthetic_ROS_Image_frames_actual_detector",
            "one_red":a,"two_red_largest":b,"empty":c,
            "threshold_px2":500,
            "point_z_semantics":"area_px2_NOT_meters",
            "target_valid_signal":True,
            "gazebo_camera":"BLOCKED_ISSUE_127",
            "depth_and_3d":"NOT_RUN",
            "real_object_precision_recall":"NOT_RUN",
            "gui":"NOT_RUN","hardware":"NOT_RUN","ch10":"HOLD",
        }
        out=Path(os.environ["CH07_74_RECEIPT"])
        out.parent.mkdir(parents=True,exist_ok=True)
        tmp=out.with_suffix(".tmp")
        tmp.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
        os.replace(tmp,out)
        print("CH07_74_REAL_ROS_RED_TARGET_AND_INVALIDATION_SCOPED_PASS",
              flush=True)
        return 0
    except (Exception,KeyboardInterrupt) as exc:
        print(f"CH07_74_FAIL type={type(exc).__name__} reason={exc}",
              flush=True)
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=="__main__":
    raise SystemExit(main())
