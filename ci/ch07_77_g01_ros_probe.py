#!/usr/bin/env python3
"""G01 real ROS/DDS admission-only probe; NO planning/physical/motor goals."""
import json
import math
import os
from pathlib import Path
import time

import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped
from rclpy.node import Node
from std_msgs.msg import Bool


class Probe(Node):
    def __init__(self):
        super().__init__("ch07_77_g01_real_ros_probe")
        self.v=self.create_publisher(Bool, "/camera/target_valid", 10)
        self.p=self.create_publisher(PointStamped, "/camera/target_3d_base", 10)
        self.received=[]
        self.poses=[]
        self.create_subscription(PointStamped,"/ch07_77/target_ready",self.received.append,10)
        self.create_subscription(PoseStamped,"/ch07_77/pregrasp_candidate",self.poses.append,10)

    def spin_for(self,secs):
        until=time.monotonic()+secs
        while time.monotonic()<until:
            rclpy.spin_once(self,timeout_sec=.025)

    def stamp_now(self,add=0.0):
        s=self.get_clock().now().nanoseconds/1e9+add
        from builtin_interfaces.msg import Time
        stamp=Time()
        stamp.sec=int(s)
        stamp.nanosec=int((s-stamp.sec)*1e9)
        return stamp

    def valid(self,flag):
        self.v.publish(Bool(data=flag))
        self.spin_for(.12)

    def point(self,xyz=(.6,.1,.5),frame="base_link",age=0):
        m=PointStamped()
        m.header.frame_id=frame
        m.header.stamp=self.stamp_now(add=age)
        m.point.x,m.point.y,m.point.z=xyz
        self.p.publish(m)
        self.spin_for(.19)
        return m


def run():
    rclpy.init()
    p=Probe()
    record={"scope":"G01_ACTUAL_ROS_DDS_TARGET_ADMISSION_ONLY_NO_GOALS",
            "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
            "invalid":[],"physical_motion":"NOT_RUN","moveit":"NOT_RUN",
            "arm_goals":0,"gripper_goals":0,"ch10":"HOLD"}
    try:
        deadline=time.monotonic()+12
        while time.monotonic()<deadline and (p.v.get_subscription_count()<1 or p.p.get_subscription_count()<1):
            p.spin_for(.2)
        assert p.v.get_subscription_count()>=1 and p.p.get_subscription_count()>=1, "mission subscriptions absent"
        p.valid(False)
        p.point()
        assert len(p.received)==0, "target without validity was published"
        cases=[
            ("nan", (float("nan"),.1,.5), "base_link",0),
            ("inf", (.6,float("inf"),.5),"base_link",0),
            ("wrong_frame", (.6,.1,.5),"camera_optical_frame",0),
            ("stale",(.6,.1,.5),"base_link",-2.0),
            ("future",(.6,.1,.5),"base_link",2.0),
            ("outside_radius",(3.0,.1,.5),"base_link",0),
            ("negative_height",(.6,.1,-.2),"base_link",0),
        ]
        for label,xyz,frame,age in cases:
            p.valid(False)
            p.valid(True)
            p.point(xyz,frame,age)
            assert len(p.received)==0, "invalid input generated target: "+label
            record["invalid"].append(label)
        # First valid input may not by itself cause a motion or ready publication.
        p.valid(False)
        p.valid(True)
        first=p.point()
        assert len(p.received)==0, "unstable single frame accepted"
        second=p.point((.605,.102,.505))
        assert len(p.received)==1, "did not accept exactly two stable fresh samples"
        assert len(p.poses)==1, "missing candidate pose"
        a=p.received[0]
        assert a.header.frame_id=="base_link"
        assert abs(a.point.x-second.point.x)<.00001
        assert abs(a.point.y-second.point.y)<.00001
        assert abs(a.point.z-second.point.z)<.00001
        pose=p.poses[0]
        assert abs(pose.pose.position.x-second.point.x)<.00001
        assert abs(pose.pose.position.z-(second.point.z+.12))<.00001
        p.point((.605,.102,.505))
        p.valid(False)
        p.valid(True)
        p.point((.8,-.1,.7))
        p.point((.8,-.1,.7))
        assert len(p.received)==1, "one-shot violated: repeated target accepted"
        assert len(p.poses)==1
        record.update(status="SCOPED_PASS",invalid_count=len(record["invalid"]),
                      actual_ros_ready_count=len(p.received),
                      actual_ros_pregrasp_candidates=len(p.poses),
                      one_shot=True,source_stamp_sec=second.header.stamp.sec,
                      target_xyz=[a.point.x,a.point.y,a.point.z],
                      pregrasp_xyz=[pose.pose.position.x,pose.pose.position.y,pose.pose.position.z])
        print("CH07_77_G01_REAL_ROS_3D_STABLE_TARGET_AND_ZERO_MOTION_SCOPED_PASS",flush=True)
    except Exception as exc:
        record["status"]="FAIL"
        record["reason"]=repr(exc)
        print("CH07_77_G01_FAIL "+repr(exc),flush=True)
        raise
    finally:
        out=Path(os.environ.get("CH07_77_G01_RECEIPT","/tmp/ch07_77_g01_receipt.json"))
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(record,indent=2,allow_nan=False)+"\n")
        p.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__=="__main__":
    run()
