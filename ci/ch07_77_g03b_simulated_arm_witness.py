#!/usr/bin/env python3
"""Ch07 #173 G03B: one bounded SIMULATION ONLY MoveGroup execution.

The sole target comes from an independently confirmed G03A OMPL plan_only
artifact. No camera, no hardcoded arbitrary target, no gripper commands.
SUCCESS requires GazeboSimSystem actual /joint_states near the joint goal
and source-Xacro wrist FK in base_link, not merely action SUCCEEDED.
"""
import json
import math
import os
from pathlib import Path
import time

import rclpy
from action_msgs.msg import GoalStatus
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from rosgraph_msgs.msg import Clock
from rclpy.qos import qos_profile_sensor_data

ARM=("joint1","joint2","joint3","joint4","joint_wrist")
FINGERS=("joint_finger1","joint_finger2")


class Observer(Node):
    def __init__(self):
        super().__init__("ch07_77_g03b_simulated_arm_execution_witness")
        self.move=ActionClient(self,MoveGroup,"/move_action")
        self.samples=[]
        self.clock_stamps=[]
        self.create_subscription(Clock,"/clock",self.on_clock,qos_profile_sensor_data)
        self.create_subscription(JointState,"/joint_states",self.on_joints,10)

    def on_clock(self,m):
        t=m.clock.sec+m.clock.nanosec*1e-9
        if t>0 and math.isfinite(t):
            self.clock_stamps.append(t)
            self.clock_stamps=self.clock_stamps[-500:]

    def on_joints(self,m):
        d=dict(zip(m.name,m.position))
        if all(n in d and math.isfinite(d[n]) for n in ARM+FINGERS):
            stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
            self.samples.append({"stamp":stamp,
                                 "arm":{n:float(d[n]) for n in ARM},
                                 "fingers":{n:float(d[n]) for n in FINGERS}})
            self.samples=self.samples[-2000:]

    def wait_ready(self,sec=30):
        deadline=time.monotonic()+sec
        while time.monotonic()<deadline:
            rclpy.spin_once(self,timeout_sec=.12)
            # The real Gazebo broadcaster stamps each JointState with
            # simulation time. These typed messages already prove the clock
            # used by the controllers is advancing; a second /clock typed
            # subscription is only DIAGNOSTIC, not a reason to block motion.
            if (len(self.samples)>=5 and self.move.server_is_ready() and
                    self.samples[-1]["stamp"]-self.samples[0]["stamp"]>=.2):
                # Warm up both ROS time sources AFTER the action server
                # appears: avoid a MoveGroup internal clock 0->simtime jump
                # immediately after it accepts a trajectory.
                warmup=time.monotonic()+3
                while time.monotonic()<warmup:
                    rclpy.spin_once(self,timeout_sec=.1)
                last_stamp=self.samples[-1]["stamp"]
                current=self.get_clock().now().nanoseconds/1e9
                if (len(self.samples)>=8 and current>0 and
                        abs(current-last_stamp)<=3.0):
                    return
        current=self.get_clock().now().nanoseconds/1e9
        raise RuntimeError(
            "G03B_READY_TIMEOUT joint_samples=%d joint_span=%.3f "
            "action_ready=%s raw_clock_samples=%d node_ros_time=%.3f "
            "last_joint_time=%.3f" % (
                len(self.samples),
                self.samples[-1]["stamp"]-self.samples[0]["stamp"]
                if self.samples else 0,
                self.move.server_is_ready(),len(self.clock_stamps),
                current,self.samples[-1]["stamp"] if self.samples else 0))

    def await_response(self,future,sec,label,on_timeout=None):
        deadline=time.monotonic()+sec
        while time.monotonic()<deadline:
            rclpy.spin_once(self,timeout_sec=.08)
            if future.done():
                return future.result()
        if on_timeout is not None:
            try:
                cancel=on_timeout()
                limit=time.monotonic()+5
                while not cancel.done() and time.monotonic()<limit:
                    rclpy.spin_once(self,timeout_sec=.1)
            except Exception:
                pass
        raise TimeoutError("G03B_"+label+"_TIMEOUT")


def original_wrist_fk(q):
    # Original G00/Ch07 5DOF Xacro: shoulder at z=.6, two planars .5 & 1.0m.
    a,b=.5,1.0
    radius=a*math.sin(q["joint2"])+b*math.sin(q["joint2"]+q["joint3"])
    return [radius*math.cos(q["joint1"]),
            radius*math.sin(q["joint1"]),
            .6+a*math.cos(q["joint2"])+b*math.cos(q["joint2"]+q["joint3"])]


def main():
    if os.environ.get("CH07_77_G03B_GAZEBO_SIM_ONLY_VERIFIED")!="YES":
        raise RuntimeError("G03B_GAZEBO_SIMULATION_OWNERSHIP_NOT_VERIFIED_ZERO_GOALS")
    path=Path(os.environ["CH07_77_G03B_TARGET"])
    goal_json=json.loads(path.read_text())
    joints=goal_json["joint_goal_rad"]
    assert set(joints)==set(ARM)
    assert all(math.isfinite(float(v)) for v in joints.values())
    report={"scope":"G03B_ACTUAL_GAZEBO_SIM_SYSTEM_MOVEIT_ARM_EXECUTION",
            "tested_source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
            "frozen_g03a_sha256":goal_json["g03a_zip_sha256"],
            "frozen_target_json":str(path),"joint_goal":joints,
            "source_wrist_xyz":goal_json["source_derived_wrist_base_link_m"],
            "moveit_6d_pose_ik":"FAIL_-31_NOT_REPAIRED_OR_CLAIMED_SUCCESS",
            "G02":"NOT_RERUN","G03A":"NOT_RERUN_FROZEN_SUCCESS",
            "G04_physical_grasp":"NOT_RUN","G04_gripper":"NOT_RUN",
            "hardware":"SIMULATION_ONLY","ch10":"HOLD",
            "status":"FAIL","goal_count":0}
    rclpy.init(args=["--ros-args","-p","use_sim_time:=true"])
    node=Observer()
    try:
        node.wait_ready()
        report["sim_clock_samples_before_goal"]=len(node.clock_stamps)
        report["sim_clock_first_s"]=node.clock_stamps[0] if node.clock_stamps else None
        report["sim_clock_latest_before_goal_s"]=node.clock_stamps[-1] if node.clock_stamps else None
        report["sim_clock_node_now_s"]=node.get_clock().now().nanoseconds/1e9
        report["gazebo_joint_state_time_before_goal_s"]=node.samples[-1]["stamp"]
        assert abs(report["sim_clock_node_now_s"]-node.samples[-1]["stamp"])<=3.0
        initial=node.samples[-1]
        report["joint_state_initial"]=initial
        request=MoveGroup.Goal()
        request.request.group_name="arm_group"
        request.request.allowed_planning_time=7.
        request.request.num_planning_attempts=3
        request.request.max_velocity_scaling_factor=.1
        request.request.max_acceleration_scaling_factor=.1
        request.planning_options.plan_only=False
        request.planning_options.replan=False
        constraints=Constraints()
        for name in ARM:
            jc=JointConstraint()
            jc.joint_name=name
            jc.position=float(joints[name])
            jc.tolerance_above=.035
            jc.tolerance_below=.035
            jc.weight=1.
            constraints.joint_constraints.append(jc)
        request.request.goal_constraints.append(constraints)
        handle=node.await_response(node.move.send_goal_async(request),12,"GOAL_ACCEPT")
        report["accepted"]=bool(handle and handle.accepted)
        report["goal_count"]=1
        if not report["accepted"]:
            raise RuntimeError("G03B_MOVEIT_GOAL_REJECTED")
        result=node.await_response(handle.get_result_async(),95,"EXECUTION_RESULT",
                                   on_timeout=handle.cancel_goal_async)
        report["action_status"]=int(result.status)
        report["moveit_error"]=int(result.result.error_code.val)
        report["planned_points"]=len(result.result.planned_trajectory.joint_trajectory.points)
        report["joint_samples"]=len(node.samples)
        report["sim_clock_latest_after_goal_s"]=node.clock_stamps[-1] if node.clock_stamps else None
        report["joint_state_final"]=node.samples[-1]
        assert report["action_status"]==GoalStatus.STATUS_SUCCEEDED
        assert report["moveit_error"]==MoveItErrorCodes.SUCCESS
        assert report["planned_points"]>0
        final=node.samples[-1]
        errors={n:abs(final["arm"][n]-float(joints[n])) for n in ARM}
        report["joint_errors_rad"]=errors
        assert max(errors.values())<=.06,"G03B_ACTUAL_JOINT_POSITION_ERROR_EXCESS"
        motion=max(abs(s["arm"][n]-initial["arm"][n])
                   for s in node.samples for n in ARM)
        report["max_real_joint_motion_rad"]=motion
        assert motion>.25,"G03B_ARM_DID_NOT_PHYSICALLY_MOVE"
        finger_delta={n:abs(final["fingers"][n]-initial["fingers"][n])
                      for n in FINGERS}
        report["finger_deltas_m"]=finger_delta
        assert max(finger_delta.values())<.004,"G03B_UNCOMMANDED_GRIPPER_MOTION"
        xyz=original_wrist_fk(final["arm"])
        report["actual_joint_derived_wrist_xyz_m"]=xyz
        report["wrist_fk_target_error_m"]=math.dist(
            xyz,goal_json["source_derived_wrist_base_link_m"])
        assert report["wrist_fk_target_error_m"]<=.07,(
            "G03B_ORIGINAL_URDF_WIRST_POSE_MISMATCH")
        report["status"]="SCOPED_PASS"
        print("CH07_77_G03B_ACTUAL_GAZEBO_ARM_MOVED_TO_G02_DERIVED_GOAL_NO_GRIPPER_SCOPED_PASS",flush=True)
    except Exception as exc:
        report["reason"]=repr(exc)
        print("CH07_77_G03B_FAIL "+repr(exc),flush=True)
        raise
    finally:
        out=Path(os.environ["CH07_77_G03B_RECEIPT"])
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=="__main__":
    main()
