#!/usr/bin/env python3
"""Ch09 §9.8 actual robot_state_publisher TF with synthetic /clock and 12 joints.

No Gazebo physics is started. Previously accepted actual Ch09 stand and
single-leg joint motion must not be rerun just to check this TF contract.
"""
import json
import math
import os
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import JointState
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage

LEGS=("fr","fl","rr","rl")
KINDS=("hip","thigh","calf")
NAMES=tuple(f"{leg}_{kind}_joint" for leg in LEGS for kind in KINDS)
DYNAMIC={f"{leg}_{kind}_link" for leg in LEGS for kind in KINDS}
STATIC={f"{leg}_foot" for leg in LEGS}|{"base_link"}


class Probe(Node):
    def __init__(self):
        super().__init__("ch09_98_actual_tf_clock_probe")
        self.js=self.create_publisher(JointState,"/joint_states",10)
        self.clock=self.create_publisher(Clock,"/clock",10)
        self.dynamic={}
        self.static={}
        self.create_subscription(TFMessage,"/tf",self.on_dynamic,20)
        static_qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE,
                              durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(TFMessage,"/tf_static",self.on_static,static_qos)

    def on_dynamic(self,msg):
        for t in msg.transforms:
            self.dynamic[t.child_frame_id] = {
                "parent":t.header.frame_id,
                "stamp_sec":t.header.stamp.sec,
                "stamp_ns":t.header.stamp.nanosec,
            }

    def on_static(self,msg):
        for t in msg.transforms:
            self.static[t.child_frame_id] = t.header.frame_id


def main():
    rclpy.init()
    probe=Probe()
    try:
        deadline=time.monotonic()+12
        count=0
        while time.monotonic()<deadline:
            sim=Clock()
            sim.clock.sec=100
            sim.clock.nanosec=(count*50_000_000)%1_000_000_000
            sim.clock.sec+=count//20
            probe.clock.publish(sim)
            msg=JointState()
            msg.header.stamp=sim.clock
            msg.name=list(NAMES)
            msg.position=[0.05 if kind=="hip" else (-0.6 if kind=="thigh" else 1.2)
                          for _leg in LEGS for kind in KINDS]
            msg.velocity=[0.0]*12
            probe.js.publish(msg)
            rclpy.spin_once(probe,timeout_sec=0.10)
            count+=1
            if DYNAMIC.issubset(probe.dynamic) and STATIC.issubset(probe.static):
                break
        if not DYNAMIC.issubset(probe.dynamic):
            raise RuntimeError(
                "CH09_98_MISSING_DYNAMIC_TF "
                + ",".join(sorted(DYNAMIC-set(probe.dynamic)))
            )
        if not STATIC.issubset(probe.static):
            raise RuntimeError(
                "CH09_98_MISSING_STATIC_TF "
                + ",".join(sorted(STATIC-set(probe.static)))
            )
        for name in DYNAMIC:
            stamp=probe.dynamic[name]["stamp_sec"]
            if not (100<=stamp<=1010):
                raise RuntimeError(f"CH09_98_WRONG_SIM_STAMP {name}={stamp}")
        if probe.static["base_link"]!="base_footprint":
            raise RuntimeError("CH09_98_BASE_ROOT_INCORRECT")
        for leg in LEGS:
            if probe.static[f"{leg}_foot"]!=f"{leg}_calf_link":
                raise RuntimeError("CH09_98_FOOT_FRAME_PARENT_INCORRECT")
        for leg in LEGS:
            for kind in KINDS:
                frame=f"{leg}_{kind}_link"
                expected="base_link" if kind=="hip" else (
                    f"{leg}_hip_link" if kind=="thigh" else f"{leg}_thigh_link"
                )
                if probe.dynamic[frame]["parent"]!=expected:
                    raise RuntimeError("CH09_98_BAD_PARENT "+frame)
        receipt={
            "chapter":"Ch09","section":"9.8","status":"SCOPED_PASS",
            "scope":"actual_ros_robot_state_publisher_sim_clock_joint_state_tf",
            "source_sha":os.environ.get("RUN_SOURCE_SHA","LOCAL_UNPINNED"),
            "joint_names":list(NAMES),
            "dynamic_frames":probe.dynamic,
            "static_frames":probe.static,
            "observed_dynamic_count":len(DYNAMIC),
            "observed_required_static_count":len(STATIC),
            "real_gazebo_physics":"NOT_RUN",
            "foot_contact":"NOT_RUN",
            "stable_stand_retest":"NOT_RUN",
            "single_leg_sine_retest":"NOT_RUN",
            "gui":"NOT_RUN","hardware":"NOT_RUN",
            "ch10":"HOLD",
        }
        out=Path(os.environ["CH09_98_RECEIPT"])
        out.parent.mkdir(parents=True,exist_ok=True)
        tmp=out.with_suffix(".tmp")
        tmp.write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
        os.replace(tmp,out)
        print(
            "CH09_98_ACTUAL_SIMTIME_TF_STATIC_AND_12_DYNAMIC_FRAMES_PASS "
            f"messages_sent={count}",flush=True,
        )
        return 0
    except (Exception,KeyboardInterrupt) as e:
        print(f"CH09_98_FAIL type={type(e).__name__} reason={e}",flush=True)
        return 1
    finally:
        probe.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=="__main__":
    raise SystemExit(main())
