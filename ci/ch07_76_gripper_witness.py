#!/usr/bin/env python3
"""Independent post-action joint measurement plus recorded controller results.

The actual source gripper_controller performed both real actions; this
independent second ROS process measures final positions and audits its logs.
No physical object, contact sensor, or grasp success is claimed.
"""
import json
import math
import os
from pathlib import Path
import re
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class Inspector(Node):
    def __init__(self):
        super().__init__("book_ch07_76_independent_joint_inspector")
        self.samples = []
        self.create_subscription(JointState,"/joint_states",self.recv,10)

    def recv(self,msg):
        joints=dict(zip(msg.name,msg.position))
        if all(j in joints and math.isfinite(joints[j])
               for j in ("joint_finger1","joint_finger2")):
            self.samples.append([float(joints["joint_finger1"]),
                                 float(joints["joint_finger2"])])


def main():
    raw=Path(sys.argv[1]).read_text()
    matches={}
    for label in ("OPEN","CLOSE"):
        pattern=(r"CH07_76_"+label+r"_ACTION_AND_MEASURED_JOINTS_PASS "
                 r"goal_m=([0-9.]+) max_error_m=([0-9.]+) "
                 r"max_joint_change_m=([0-9.]+) "
                 r"joint1_m=([0-9.]+) joint2_m=([0-9.]+)")
        m=re.search(pattern,raw)
        if not m:
            raise RuntimeError("CH07_76_NO_ACTION_EVIDENCE_"+label)
        goal,err,delta,j1,j2=map(float,m.groups())
        assert err<=0.003 and all(abs(j-goal)<=0.003 for j in (j1,j2))
        assert 0.0<=goal<=0.025
        matches[label]={"command_m":goal,"measured_m":[j1,j2],
                        "error_m":err,"reported_motion_m":delta}
    assert abs(matches["OPEN"]["command_m"]-0.005)<1e-6
    assert abs(matches["CLOSE"]["command_m"]-0.020)<1e-6
    assert matches["CLOSE"]["reported_motion_m"]>=0.01
    assert "CH07_76_SEQUENCE_OPEN_RESULT_THEN_CLOSE_REAL_FEEDBACK_PASS" in raw

    rclpy.init()
    n=Inspector()
    try:
        end=time.monotonic()+10
        while time.monotonic()<end and len(n.samples)<15:
            rclpy.spin_once(n,timeout_sec=0.15)
        if len(n.samples)<15:
            raise RuntimeError("CH07_76_INDEPENDENT_REAL_JOINT_STATE_MISSING")
        final=n.samples[-1]
        if max(abs(p-0.020) for p in final)>0.003:
            raise RuntimeError("CH07_76_POST_ACTION_TARGET_NOT_MEASURED")
        evidence={
            "chapter":"Ch07", "section":"7.6",
            "scope":"real_gazebo_gz_ros2_control_two_prismatic_joint_actions_only",
            "action":"/gripper_group_controller/follow_joint_trajectory",
            "joints":["joint_finger1","joint_finger2"],
            "units":"meters",
            "actions":matches,
            "independent_final_position_m":final,
            "independent_joint_state_samples":len(n.samples),
            "source_success":"real_action_SUCCEEDED_and_measured_joints",
            "gazebo_controller":"REQUIRES_WRAPPER_PLUGIN_PROOF",
            "real_object_grasp":"NOT_RUN",
            "friction_and_contact":"NOT_RUN","rgbd_camera":"BLOCKED_ISSUE_127",
            "moveit_gripper_integration":"NOT_RUN","real_hardware":"NOT_RUN",
            "ch10":"HOLD",
        }
        path=Path(os.environ["CH07_76_RECEIPT"])
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(".tmp")
        tmp.write_text(json.dumps(evidence,sort_keys=True,indent=2)+"\n")
        os.replace(tmp,path)
        print(
            "CH07_76_INDEPENDENT_REAL_GAZEBO_FINGER_ACTION_AND_FINAL_JOINTS_PASS "
            f"final_positions_m={final} n={len(n.samples)}",
            flush=True,
        )
        return 0
    finally:
        n.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"CH07_76_INDEPENDENT_FAIL reason={exc}",flush=True)
        sys.exit(1)
