#!/usr/bin/env python3
"""Ch07 #173 G04A actual OGRE2 RGB-D graspable small rod → 3D target witness.

No synthetic images/depth, no MoveIt, no arm/gripper Goal. Exact observed
timestamps/frame IDs/target XYZ saved even on failure.
"""
import json
import os
from pathlib import Path
import time

import rclpy
from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo, JointState
from std_msgs.msg import Bool


def stamp(message):
    h=message.header.stamp
    return h.sec+h.nanosec*1e-9


class Witness(Node):
    def __init__(self):
        super().__init__("ch07_77_g04a_real_rgbd_witness")
        self.images=[];self.depth=[];self.info=[];self.pixels=[]
        self.targets=[];self.ready=[];self.valid=0;self.joints=0
        self.create_subscription(Image,"/camera/image_raw",
                                 lambda x:self.add("images",x),qos_profile_sensor_data)
        self.create_subscription(Image,"/camera/depth/image_raw",
                                 lambda x:self.add("depth",x),qos_profile_sensor_data)
        self.create_subscription(CameraInfo,"/camera/camera_info",
                                 lambda x:self.add("info",x),qos_profile_sensor_data)
        self.create_subscription(PointStamped,"/camera/target_pixel",
                                 lambda x:self.add("pixels",x),10)
        self.create_subscription(PointStamped,"/camera/target_3d_base",
                                 lambda x:self.add("targets",x),10)
        self.create_subscription(PointStamped,"/ch07_77/target_ready",
                                 lambda x:self.add("ready",x),10)
        self.create_subscription(Bool,"/camera/target_valid",self.on_valid,10)
        self.create_subscription(JointState,"/joint_states",self.on_joint,10)

    def add(self,field,m):
        a=getattr(self,field)
        if len(a)<40:
            entry={"stamp":stamp(m),"frame":m.header.frame_id}
            if isinstance(m,PointStamped):
                entry["xyz"]=[float(m.point.x),float(m.point.y),float(m.point.z)]
            if isinstance(m,Image):
                entry.update(encoding=m.encoding,height=m.height,width=m.width,data_len=len(m.data))
            if isinstance(m,CameraInfo):
                entry.update(width=m.width,height=m.height,K=[float(i) for i in m.k])
            a.append(entry)

    def on_valid(self,m):
        if m.data:
            self.valid+=1

    def on_joint(self,m):
        if "joint_wrist" in m.name and "joint_finger1" in m.name:
            self.joints+=1


def run():
    rclpy.init()
    w=Witness()
    report={"scope":"G04A_GRASPABLE_DYNAMIC_ROD_REAL_RGBD_AND_MISSION_TARGET",
            "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
            "G03_MoveIt":"NOT_RUN","G04B_physical_grasp":"NOT_RUN","Ch10":"HOLD",
            "status":"FAIL"}
    try:
        stop=time.monotonic()+float(os.environ.get("CH07_77_G04A_TIMEOUT","54"))
        readiness=Path(os.environ.get("CH07_77_G04A_WITNESS_READY_FILE",
                                      "/tmp/ch07_77_g04a_witness_ready"))
        discovered=False
        while time.monotonic()<stop:
            rclpy.spin_once(w,timeout_sec=.1)
            if not discovered and w.count_publishers("/ch07_77/target_ready")>=1:
                # This node's subscription exists before the producing
                # detector is started. A local flag avoids slow repeated
                # ros2cli daemon startup / stale graph cache on CI.
                readiness.parent.mkdir(parents=True,exist_ok=True)
                readiness.write_text("G04A_WITNESS_DDS_PUBLISHER_DISCOVERED\n")
                discovered=True
            if len(w.images)>=3 and len(w.depth)>=3 and len(w.info)>=3 and len(w.pixels)>=2 and len(w.targets)>=2 and len(w.ready)>=1 and w.joints>=2:
                break
        report.update(actual_image_count=len(w.images),
                      actual_depth_count=len(w.depth),
                      actual_camera_info_count=len(w.info),
                      actual_target_pixel_count=len(w.pixels),
                      actual_3d_target_count=len(w.targets),
                      actual_ready_count=len(w.ready),
                      valid_positive_count=w.valid,
                      actual_joint_samples=w.joints,
                      messages={n:getattr(w,n) for n in
                                ("images","depth","info","pixels","targets","ready")})
        assert len(w.images)>=3 and len(w.depth)>=3 and len(w.info)>=3, "REAL_SENSOR_STREAM_MISSING"
        assert len(w.pixels)>=2 and w.valid>=2, "RED_DETECTOR_DID_NOT_ACCEPT_REAL_IMAGE"
        assert len(w.targets)>=2, "RGB_DEPTH_K_TF_NOT_PROJECTED"
        assert len(w.ready)==1, "MISSION_TWO_FRAME_ADMISSION_NOT_OBSERVED"
        assert w.joints>=2, "GAZEBO_JOINT_STATES_FOR_TF_MISSING"
        assert all(v["frame"]=="camera_optical_frame" for v in
                   w.images[:3]+w.depth[:3]+w.info[:3]+w.pixels[:2])
        assert all(v["frame"]=="base_link" for v in w.targets[:2]+w.ready[:1])
        for v in w.images[:3]:
            assert v["width"]==640 and v["height"]==480
            assert v["data_len"]>0
        for v in w.depth[:3]:
            assert v["encoding"]=="32FC1", v["encoding"]
            assert v["data_len"]==640*480*4
        pixel_stamps={round(x["stamp"],3) for x in w.pixels}
        assert any(abs(a["stamp"]-b["stamp"])<=0.08
                   for a in w.targets for b in w.pixels), "PIXEL_TO_3D_STAMP_NOT_MATCHED"
        assert any(abs(a["stamp"]-b["stamp"])<=0.08
                   for a in w.ready for b in w.targets), "MISSION_TARGET_NOT_FROM_SENSOR"
        # Gate checks frame, freshness, finite xyz; this independent bound
        # proves the measured coordinate comes from expected real object
        # region, not from constant legacy move_arm(1.0...).
        x,y,z=w.targets[-1]["xyz"]
        assert .765<=x<=.81 and abs(y)<=.09 and 1.80<=z<=2.08, (x,y,z)
        report["status"]="SCOPED_PASS"
        print("CH07_77_G04A_REAL_OGRE2_RGBD_RED_DETECTOR_3D_TARGET_NO_GOAL_SCOPED_PASS",flush=True)
    except Exception as exc:
        report["reason"]=repr(exc)
        print("CH07_77_G04A_FAIL "+repr(exc),flush=True)
        raise
    finally:
        path=Path(os.environ.get("CH07_77_G04A_RECEIPT","/tmp/ch07_77_g04a_receipt.json"))
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        w.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__=="__main__":
    run()
