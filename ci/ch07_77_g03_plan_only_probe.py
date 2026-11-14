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

    def plan_position_joint_goal(self, joint_goal):
        """Real MoveGroup OMPL planning from analytic source-derived 5DOF joints.

        This is NOT a 6D KDL Pose IK success and not an authorized grasp pose.
        """
        goal=MoveGroup.Goal()
        goal.request.group_name="arm_group"
        goal.request.allowed_planning_time=7.0
        goal.request.num_planning_attempts=5
        goal.planning_options.plan_only=True
        goal.planning_options.replan=False
        constraints=Constraints()
        for name in ARM:
            jc=JointConstraint()
            jc.joint_name=name
            jc.position=float(joint_goal[name])
            jc.tolerance_above=.04
            jc.tolerance_below=.04
            jc.weight=1.0
            constraints.joint_constraints.append(jc)
        goal.request.goal_constraints.append(constraints)
        sent=self.awaited(self.move.send_goal_async(goal),12,"JOINT_GOAL_ACCEPT")
        entry={"joint_goal":joint_goal,"move_goal_accepted":bool(sent and sent.accepted)}
        if not entry["move_goal_accepted"]:
            return entry
        envelope=self.awaited(sent.get_result_async(),30,"JOINT_PLAN_RESULT")
        entry["action_status"]=int(envelope.status)
        entry["moveit_error"]=int(envelope.result.error_code.val)
        plan=envelope.result.planned_trajectory.joint_trajectory
        entry["trajectory_joint_names"]=list(plan.joint_names)
        entry["trajectory_points"]=len(plan.points)
        return entry

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


def geometric_position_only_ik(x,y,z):
    """Exact 2R position IK for Ch07 ORIGINAL Xacro geometry.

    In original Xacro the shoulder joint2 is at z=0.6m (base .1 + link1 .5),
    joint3 follows a 0.5m link and the wrist follows two collinear 0.5m links.
    Link3 joint4 rotates about its own z: wrist origin is unaffected by
    q4; joint_wrist rotates the tool without changing wrist origin.
    This solves POSITION ONLY. No 6D orientation or collision proof.
    """
    a,b=0.5,1.0
    radius=math.hypot(x,y)
    dz=z-0.6
    c=(radius*radius+dz*dz-a*a-b*b)/(2*a*b)
    if not math.isfinite(c) or abs(c)>1:
        raise ValueError("G03_POSITION_OUTSIDE_ORIGINAL_2R_REACH")
    angle3=math.acos(max(-1.0,min(1.0,c)))
    angle2=math.atan2(radius,dz)-math.atan2(b*math.sin(angle3),
                                             a+b*math.cos(angle3))
    yaw=math.atan2(y,x)
    goal=dict(zip(ARM,(yaw,angle2,angle3,0.0,0.0)))
    limits={"joint1":(-3.14159,3.14159),
            "joint2":(-1.57079,1.57079),
            "joint3":(-2.0944,2.0944),
            "joint4":(-3.14159,3.14159),
            "joint_wrist":(-1.5708,1.5708)}
    for name,value in goal.items():
        lower,upper=limits[name]
        if not lower<=value<=upper:
            raise ValueError("G03_ORIGINAL_JOINT_LIMIT_VIOLATION_"+name)
    forward_r=a*math.sin(angle2)+b*math.sin(angle2+angle3)
    forward_z=0.6+a*math.cos(angle2)+b*math.cos(angle2+angle3)
    assert math.hypot(forward_r-radius,forward_z-z)<1e-7
    return goal


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
        # The arm has only 5 controlled DOF. A fully constrained six-axis
        # KDL Pose IK request can legitimately return -31 for every attempt.
        # Do not lower MoveIt tolerances or fake an IK success: instead use
        # the EXACT original planar 2R position-only kinematics to construct
        # joint constraints and ask the REAL OMPL MoveGroup to plan them.
        if not report.get("plan_only_succeeded"):
            report["pose_ik_failure_codes"]=[
                a.get("ik_error") for a in report["attempts"]]
            report["position_only_fallbacks"]=[]
            frozen_data=json.loads(frozen.read_text())
            surface=frozen_data["measured_surface_point_base_link_m"]
            offset=frozen_data["planning_staging_offset_from_surface_m"]
            base=[surface[i]+offset[i] for i in range(3)]
            for i,xyz in enumerate((base,[base[0]-.07,base[1],base[2]-.08],
                                    [base[0]-.12,base[1],base[2]-.13])):
                sample={"label":"measured_g02_2r_position_only_"+str(i),
                        "derived_wrist_xyz":xyz}
                try:
                    joint_goal=geometric_position_only_ik(*xyz)
                    sample.update(node.plan_position_joint_goal(joint_goal))
                except Exception as exc:
                    sample["exception"]=repr(exc)
                report["position_only_fallbacks"].append(sample)
                if (sample.get("moveit_error")==MoveItErrorCodes.SUCCESS and
                        sample.get("action_status")==GoalStatus.STATUS_SUCCEEDED and
                        sample.get("trajectory_points",0)>0):
                    report["plan_only_succeeded"]=sample["label"]
                    report["acceptance_kind"]="2R_POSITION_ONLY_REAL_MOVEIT_OMPL_JOINT_PLAN"
                    report["6d_pose_ik"] = "FAIL_NO_IK_SOLUTION_-31"
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
