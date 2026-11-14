#!/usr/bin/env python3
"""Ch07 Issue #173 G03A: independent real Jazzy MoveIt 5-DOF IK and plan_only.

Uses G02 verified original ROS RGB-D surface sample as explicit REPLAY data.
No fabricated sensor messages are passed as a new G02 result. This probe
never calls a FollowJointTrajectory action or asks MoveGroup to execute.
All attempts and numerical MoveIt errors are persisted, even on failure.
"""
import json
import math
import os
from pathlib import Path
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from moveit_msgs.srv import GetPositionIK
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory

ARM=("joint1","joint2","joint3","joint4","joint_wrist")


class Witness(Node):
    def __init__(self):
        super().__init__("ch07_77_g03_moveit_plan_only")
        self.ik=self.create_client(GetPositionIK,"/compute_ik")
        self.move=ActionClient(self,MoveGroup,"/move_action")
        self.states=[]
        self.actuator_commands=0
        self.create_subscription(JointState,"/joint_states",self.on_joint,10)
        self.create_subscription(JointTrajectory,"/arm_group_controller/joint_trajectory",
                                 self.on_motion_command,10)

    def on_motion_command(self,msg):
        self.actuator_commands+=1

    def on_joint(self,msg):
        d=dict(zip(msg.name,msg.position))
        if all(n in d and math.isfinite(d[n]) for n in ARM):
            self.states.append({n:float(d[n]) for n in ARM})
            self.states=self.states[-50:]

    def ready(self,limit=36):
        end=time.monotonic()+limit
        while time.monotonic()<end:
            rclpy.spin_once(self,timeout_sec=.15)
            if self.states and self.ik.service_is_ready() and self.move.server_is_ready():
                return
        raise RuntimeError("G03_REAL_GAZEBO_JOINTS_MOVEIT_SERVERS_NOT_READY")

    def awaited(self,future,wall_sec,label):
        end=time.monotonic()+wall_sec
        while time.monotonic()<end:
            rclpy.spin_once(self,timeout_sec=.07)
            if future.done():
                return future.result()
        raise TimeoutError("G03_TIMEOUT_"+label)

    def attempt(self,pose):
        request=GetPositionIK.Request()
        ik=request.ik_request
        ik.group_name="arm_group"
        ik.avoid_collisions=True
        ik.pose_stamped=pose
        ik.timeout.sec=4
        ik.robot_state.joint_state.name=list(ARM)
        ik.robot_state.joint_state.position=[
            self.states[-1][name] for name in ARM
        ]
        ik.robot_state.is_diff=False
        result=self.awaited(self.ik.call_async(request),9,"IK_RESPONSE")
        err=int(result.error_code.val)
        js=result.solution.joint_state
        d=dict(zip(js.name,js.position))
        entry={"ik_error":err,"ik_joint_names":list(js.name),
               "ik_positions":{n:float(d[n]) for n in ARM if n in d}}
        if err!=MoveItErrorCodes.SUCCESS or any(n not in d for n in ARM):
            return entry
        goal=MoveGroup.Goal()
        goal.request.group_name="arm_group"
        goal.request.allowed_planning_time=5.0
        goal.request.num_planning_attempts=3
        goal.planning_options.plan_only=True
        goal.planning_options.replan=False
        c=Constraints()
        for name in ARM:
            jc=JointConstraint()
            jc.joint_name=name
            jc.position=float(d[name])
            jc.tolerance_above=.04
            jc.tolerance_below=.04
            jc.weight=1.0
            c.joint_constraints.append(jc)
        goal.request.goal_constraints.append(c)
        sent=self.awaited(self.move.send_goal_async(goal),10,"MOVE_GOAL_ACCEPT")
        entry["move_goal_accepted"]=bool(sent and sent.accepted)
        if not entry["move_goal_accepted"]:
            return entry
        envelope=self.awaited(sent.get_result_async(),28,"MOVE_PLAN_RESULT")
        entry["action_status"]=int(envelope.status)
        entry["moveit_error"]=int(envelope.result.error_code.val)
        traj=envelope.result.planned_trajectory.joint_trajectory
        entry["trajectory_joint_names"]=list(traj.joint_names)
        entry["trajectory_points"]=len(traj.points)
        return entry


def poses_from_g02(path):
    data=json.loads(path.read_text())
    surface=data["measured_surface_point_base_link_m"]
    off=data["planning_staging_offset_from_surface_m"]
    base=[surface[i]+off[i] for i in range(3)]
    # Both test-only options are derived from the measured real target.
    # G03A discovers whether Ch07 5DOF can actually produce IK; never
    # certify either as a physical grasp pose or a valid bin approach.
    positions=[base,[base[0]-.07,base[1],base[2]-.08],
               [base[0]-.12,base[1],base[2]-.13]]
    # Old mission default horizontal tool plus neutral tool orientation.
    orientations=[(0.,.7071067811865476,0.,.7071067811865476),
                  (0.,0.,0.,1.),
                  (0.,.5,0.,.8660254037844386)]
    for i,pos in enumerate(positions):
        for j,q in enumerate(orientations):
            p=PoseStamped()
            p.header.frame_id="base_link"
            p.pose.position.x,p.pose.position.y,p.pose.position.z=pos
            (p.pose.orientation.x,p.pose.orientation.y,
             p.pose.orientation.z,p.pose.orientation.w)=q
            yield f"target_derived_{i}_orientation_{j}",p


def main():
    out=Path(os.environ["CH07_77_G03_RECEIPT"])
    frozen=Path(os.environ["CH07_77_G02_FROZEN_TARGET"])
    report={"scope":"G03A_G02_REAL_SOURCE_TARGET_REPLAY_MOVEIT_IK_OMPL_PLAN_ONLY",
            "test_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
            "frozen_target_source":str(frozen),
            "frozen_g02_artifact_sha256":json.loads(frozen.read_text())["g02_artifact_zip_sha256"],
            "G02_live_rgbd_in_this_run":"NOT_RUN_ACCEPTED_G02_REPLAY_ONLY",
            "moveit_execute":"NOT_RUN","G04_physical_grasp":"NOT_RUN",
            "arm_goal_execution_count":0,"gripper_goal_execution_count":0,
            "status":"FAIL","attempts":[],"ch10":"HOLD"}
    rclpy.init(args=["--ros-args","-p","use_sim_time:=true"])
    node=Witness()
    try:
        node.ready()
        report["gazebo_joint_states_present"]=len(node.states)>0
        report["gazebo_start_joint_state"]=node.states[-1]
        for label,pose in poses_from_g02(frozen):
            attempt={"label":label,
                     "staging_xyz":[pose.pose.position.x,pose.pose.position.y,
                                     pose.pose.position.z],
                     "orientation_xyzw":[pose.pose.orientation.x,pose.pose.orientation.y,
                                         pose.pose.orientation.z,pose.pose.orientation.w]}
            try: attempt.update(node.attempt(pose))
            except Exception as e: attempt["exception"]=repr(e)
            report["attempts"].append(attempt)
            if (attempt.get("moveit_error")==MoveItErrorCodes.SUCCESS and
                    attempt.get("action_status")==GoalStatus.STATUS_SUCCEEDED and
                    attempt.get("trajectory_points",0)>0):
                report["plan_only_succeeded"]=attempt["label"]
                break
        report["arm_controller_topic_count"]=node.actuator_commands
        assert report.get("plan_only_succeeded"),"NO_FROZEN_TARGET_DERIVED_MOVEIT_PLAN_SUCCEEDED"
        assert node.actuator_commands==0,"PLAN_ONLY_PUBLISHED_PHYSICAL_TRAJECTORY"
        report["status"]="SCOPED_PASS"
        print("CH07_77_G03A_ACTUAL_MOVEIT_5DOF_G02_TARGET_DERIVED_PLAN_ONLY_ZERO_MOTOR_COMMANDS_SCOPED_PASS",flush=True)
    except Exception as exc:
        report["reason"]=repr(exc)
        print("CH07_77_G03A_FAIL "+repr(exc),flush=True)
        raise
    finally:
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2)+"\n")
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=="__main__":
    main()
