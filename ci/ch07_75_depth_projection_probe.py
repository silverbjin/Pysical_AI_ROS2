#!/usr/bin/env python3
"""Real ROS pub/sub acceptance of Ch07 §7.5 on synthetic aligned inputs.

No Gazebo sensor or depth alignment implied: the actual camera is BLOCKED #127.
"""
import copy
import json
import math
import os
from pathlib import Path
import struct
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PointStamped
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import Bool


class Probe(Node):
    def __init__(self):
        super().__init__("ch07_75_projection_probe")
        self.pixel = self.create_publisher(PointStamped, "/camera/target_pixel", 10)
        self.valid = self.create_publisher(Bool, "/camera/target_valid", 10)
        self.depth = self.create_publisher(Image, "/camera/depth/image_raw",
                                           qos_profile_sensor_data)
        self.info = self.create_publisher(CameraInfo, "/camera/camera_info",
                                          qos_profile_sensor_data)
        self.received = []
        self.create_subscription(PointStamped, "/camera/target_3d_base",
                                 self.received.append, 10)

    def spin(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def inputs(self, depth_m, encoding="32FC1", invalid_k=False,
               bad_frame=False, stale=False, bad_sync=False):
        stamp = self.get_clock().now().to_msg()
        if stale:
            stamp.sec -= 5
        frame = "wrong_optical" if bad_frame else "camera_optical_frame"
        info = CameraInfo()
        info.header.stamp = stamp
        info.header.frame_id = frame
        info.width, info.height = 80, 60
        info.k = [60.0, 0.0, 40.0, 0.0, 60.0, 30.0, 0.0, 0.0, 1.0]
        if invalid_k:
            info.k[0] = 0.0
        image = Image()
        image.header = copy.deepcopy(info.header)
        image.width, image.height = 80, 60
        image.encoding = encoding
        image.is_bigendian = 0
        if encoding == "16UC1":
            image.step = 80*2
            raw = struct.pack("<H", round(depth_m * 1000))
        else:
            image.step = 80*4
            raw = struct.pack("<f", depth_m)
        image.data = raw * (80*60)
        if bad_sync:
            image.header.stamp.sec -= 2
        pixel = PointStamped()
        pixel.header.stamp = stamp
        pixel.header.frame_id = frame
        pixel.point.x, pixel.point.y = 48., 34.
        pixel.point.z = 6400.0  # a pixel AREA from §7.4, *not* depth
        return stamp, info, image, pixel

    def emit(self, info, image, pixel, valid):
        self.valid.publish(Bool(data=valid))
        self.info.publish(info)
        self.depth.publish(image)
        self.pixel.publish(pixel)

    def check(self, case, should_publish, depth_m=0.5, encoding="32FC1", **kw):
        self.spin(0.12)
        # Don't let a previous true state authorize a new invalid target.
        if not should_publish:
            for _ in range(5):
                self.valid.publish(Bool(data=False))
                self.spin(0.05)
        stamp, info, image, pixel = self.inputs(depth_m,encoding,**kw)
        signature = (stamp.sec, stamp.nanosec)
        end = time.monotonic() + (3.5 if should_publish else 0.85)
        matching = []
        while time.monotonic() < end:
            self.emit(info,image,pixel,should_publish or case != "invalid_validity")
            rclpy.spin_once(self,timeout_sec=0.08)
            matching = [m for m in self.received
                        if (m.header.stamp.sec,m.header.stamp.nanosec)==signature]
            if should_publish and matching:
                break
        if should_publish:
            if not matching:
                raise RuntimeError("CH07_75_NO_VALID_PROJECTED_POINT case="+case)
            expected_z = depth_m + 0.4
            expected_x = 0.2 + 8*depth_m/60
            expected_y = 0.1 + 4*depth_m/60
            point = matching[-1]
            if point.header.frame_id != "base_link":
                raise RuntimeError("CH07_75_INCORRECT_FRAME case="+case)
            error = math.sqrt(sum((a-b)**2 for a,b in zip(
                (point.point.x,point.point.y,point.point.z),
                (expected_x,expected_y,expected_z))))
            if error > 0.002:
                raise RuntimeError(f"CH07_75_PROJECTED_XYZ_ERROR case={case} error={error}")
            print(f"CH07_75_{case}_PASS error_m={error:.7f} "
                  f"depth_m={depth_m} area_not_depth_px2=6400",flush=True)
            return {"case":case,"xyz_error_m":error,"encoding":encoding}
        if matching:
            raise RuntimeError("CH07_75_INVALID_INPUT_PUBLISHED_3D case="+case)
        print("CH07_75_"+case+"_FAIL_CLOSED_PASS",flush=True)
        return {"case":case,"invalid_published":False}


def main():
    rclpy.init()
    node=Probe()
    try:
        end=time.monotonic()+9
        while time.monotonic()<end:
            if all(p.get_subscription_count()>0 for p in
                   (node.pixel,node.valid,node.depth,node.info)):
                break
            node.spin(0.12)
        else:
            raise RuntimeError("CH07_75_INPUT_SUBSCRIBERS_MISSING")

        results=[node.check("VALID_32FC1",True,0.5,"32FC1"),
                 node.check("VALID_16UC1",True,0.75,"16UC1"),
                 node.check("INVALID_DEPTH_NAN",False,math.nan),
                 node.check("INVALID_DEPTH_ZERO",False,0.0),
                 node.check("INVALID_CAMERA_K",False,0.5,invalid_k=True),
                 node.check("INVALID_STALE_STAMP",False,0.5,stale=True),
                 node.check("INVALID_MISALIGNED_STAMP",False,0.5,bad_sync=True),
                 node.check("INVALID_OPTICAL_FRAME",False,0.5,bad_frame=True),
                 node.check("invalid_validity",False,0.5)]
        receipt={
            "status":"SCOPED_PASS", "chapter":"Ch07", "section":"7.5",
            "scope":"synthetic_aligned_depth_k_pointstamp_static_tf_actual_ros",
            "results":results, "accepted_valid_count":2,
            "invalid_cases_with_no_3d_publication":7,
            "target_is_not_grasp_pose":True,
            "input_pixel_point_z":"area_px2_not_depth",
            "actual_gazebo_rgbd":"BLOCKED_ISSUE_127",
            "actual_depth_alignment":"NOT_RUN", "moving_wrist_tf":"NOT_RUN",
            "hardware":"NOT_RUN","ch10":"HOLD",
        }
        output=Path(os.environ["CH07_75_RECEIPT"])
        output.parent.mkdir(parents=True,exist_ok=True)
        tmp=output.with_suffix(".tmp")
        tmp.write_text(json.dumps(receipt,sort_keys=True,indent=2,allow_nan=False)+"\n")
        os.replace(tmp,output)
        print("CH07_75_ACTUAL_ROS_SYNTHETIC_DEPTH_CAMERAINFO_TF_SCOPED_PASS",flush=True)
        return 0
    except (Exception,KeyboardInterrupt) as e:
        print(f"CH07_75_FAIL type={type(e).__name__} reason={e}",flush=True)
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__=="__main__":
    raise SystemExit(main())
