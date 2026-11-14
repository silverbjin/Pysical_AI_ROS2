#!/usr/bin/env python3
"""Issue #173 G04B: simulation-only REAL physics 24mm rod pick/lift/place.

No teleport, fixed joint, fake attachment, simulated pose injection, or
hardware. This test reuses accepted robot components but exercises only the
previously untested *contact* boundary. The target comes from a NEW fixture,
not a newly captured camera frame; full original RGB-D is a later G05 gate.
"""
import json,math,os,re,subprocess,time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints,JointConstraint,MoveItErrorCodes
from trajectory_msgs.msg import JointTrajectoryPoint
from sensor_msgs.msg import JointState

ARM=("joint1","joint2","joint3","joint4","joint_wrist")
FINGERS=("joint_finger1","joint_finger2")
POSE_RE=re.compile(r"Pose \[ XYZ \(m\) \] \[ RPY \(rad\) \]:\s*\n\s*\[\s*([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s*\]")

def rod_pose():
    res=subprocess.run(["gz","model","--model","g04_grasp_cylinder","--pose"],
                       capture_output=True,text=True,timeout=10,check=True)
    m=POSE_RE.search(res.stdout)
    if m is None: raise RuntimeError("G04B_NATIVE_GZ_ROD_POSE_UNPARSEABLE "+res.stdout[-500:])
    return [float(x) for x in m.groups()]


def arm_ik_tilted_fingers(x,y,z):
    """Exact original source 2R POSITION IK; wrist q5 preserves 0.72rad tilted finger direction.

    Does NOT claim 6D Pose IK success or MoveIt collision-free grasp pose.
    Actual collision feasibility is validated separately by real Gazebo.
    """
    radius=math.hypot(x,y);dz=z-.6;a=.5;b=1.
    c=(radius**2+dz**2-a*a-b*b)/(2*a*b)
    if not math.isfinite(c) or abs(c)>1:raise ValueError("G04B_UNREACHABLE_WRIST")
    q3=math.acos(c)
    q2=math.atan2(radius,dz)-math.atan2(b*math.sin(q3),a+b*math.cos(q3))
    # Source collision wrist extends local z<=.06, fingers local z=.06..14.
    # The dynamic rod must enter between fingers at local z≈.12, never
    # into the wrist box. Tool tilt is the G04B geometry receipt .72rad.
    target=dict(zip(ARM,[math.atan2(y,x),q2,q3,0.,.72-(q2+q3)]))
    limits={"joint1":(-3.14159,3.14159),"joint2":(-1.57079,1.57079),
            "joint3":(-2.0944,2.0944),"joint4":(-3.14159,3.14159),
            "joint_wrist":(-1.5708,1.5708)}
    for name,q in target.items():
        lo,hi=limits[name]
        if not lo<=q<=hi:raise ValueError("G04B_JOINT_LIMIT_"+name)
    assert math.hypot(
        a*math.sin(q2)+b*math.sin(q2+q3)-radius,
        .6+a*math.cos(q2)+b*math.cos(q2+q3)-z)<1e-7
    return target


class Witness(Node):
    def __init__(self):
        super().__init__("ch07_77_g04b_actual_gazebo_contact_witness")
        self.move=ActionClient(self,MoveGroup,"/move_action")
        self.grip=ActionClient(self,FollowJointTrajectory,
                               "/gripper_group_controller/follow_joint_trajectory")
        self.joints=[]
        self.create_subscription(JointState,"/joint_states",self.on_state,10)

    def on_state(self,m):
        d=dict(zip(m.name,m.position))
        if all(n in d and math.isfinite(d[n]) for n in ARM+FINGERS):
            t=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
            self.joints.append({"stamp":t,
                "arm":{n:float(d[n]) for n in ARM},
                "fingers":{n:float(d[n]) for n in FINGERS}})
            self.joints=self.joints[-5000:]

    def spin_for(self,sec):
        stop=time.monotonic()+sec
        while time.monotonic()<stop:rclpy.spin_once(self,timeout_sec=.08)

    def wait_ready(self,sec=40):
        until=time.monotonic()+sec
        while time.monotonic()<until:
            rclpy.spin_once(self,timeout_sec=.12)
            if (len(self.joints)>=8 and self.move.server_is_ready() and
                  self.grip.server_is_ready() and
                  self.joints[-1]["stamp"]-self.joints[0]["stamp"]>.3):
                self.spin_for(2.5)
                if abs(self.get_clock().now().nanoseconds/1e9-
                       self.joints[-1]["stamp"])<3: return
        raise RuntimeError("G04B_ACTION_SERVERS_OR_REAL_JOINT_STATES_NOT_READY")

    def await_future(self,future,label,timeout=100,cancel=None):
        stop=time.monotonic()+timeout
        while time.monotonic()<stop:
            rclpy.spin_once(self,timeout_sec=.10)
            if future.done():return future.result()
        if cancel is not None:
            try:
                cf=cancel();self.spin_for(2)
            except Exception:pass
        raise TimeoutError("G04B_TIMEOUT_"+label)

    def arm_goal(self,label,xyz,plan_only=False):
        target=arm_ik_tilted_fingers(*xyz)
        goal=MoveGroup.Goal()
        goal.request.group_name="arm_group"
        goal.request.allowed_planning_time=6.
        goal.request.num_planning_attempts=3
        goal.request.max_velocity_scaling_factor=.17
        goal.request.max_acceleration_scaling_factor=.17
        goal.planning_options.plan_only=bool(plan_only)
        goal.planning_options.replan=False
        c=Constraints()
        for name in ARM:
            jc=JointConstraint()
            jc.joint_name=name
            jc.position=target[name]
            jc.tolerance_above=.035
            jc.tolerance_below=.035
            jc.weight=1.
            c.joint_constraints.append(jc)
        goal.request.goal_constraints.append(c)
        before=self.joints[-1] if self.joints else {}
        handle=self.await_future(self.move.send_goal_async(goal),
                                 label+"_ACCEPT",15)
        if not handle or not handle.accepted:
            raise RuntimeError("G04B_ARM_GOAL_REJECTED_"+label)
        outcome=self.await_future(handle.get_result_async(),
                                  label+"_RESULT",100,handle.cancel_goal_async)
        row={"name":label,"plan_only":plan_only,"goal_joint_positions":target,
             "action_status":int(outcome.status),
             "moveit_error":int(outcome.result.error_code.val),
             "planned_points":len(outcome.result.planned_trajectory.joint_trajectory.points),
             "initial_joint_state":before,
             "final_joint_state":self.joints[-1] if self.joints else None}
        if (row["action_status"]!=GoalStatus.STATUS_SUCCEEDED or
            row["moveit_error"]!=MoveItErrorCodes.SUCCESS or
            row["planned_points"]==0):
            raise RuntimeError("G04B_ARM_"+label+"_NOT_SUCCEEDED_"+str(row))
        if not plan_only:
            errors={n:abs(self.joints[-1]["arm"][n]-target[n]) for n in ARM}
            row["measured_joint_errors_rad"]=errors
            if max(errors.values())>.075:
                raise RuntimeError("G04B_ARM_"+label+"_JOINT_ERROR_EXCESS_"+str(errors))
        return row

    def grip_goal(self,label,q):
        if not (0.0<=q<=.025):raise ValueError("G04B_GRIPPER_LIMIT")
        goal=FollowJointTrajectory.Goal()
        goal.trajectory.joint_names=list(FINGERS)
        pt=JointTrajectoryPoint()
        pt.positions=[q,q];pt.time_from_start.sec=2
        goal.trajectory.points=[pt]
        h=self.await_future(self.grip.send_goal_async(goal),label+"_ACCEPT",15)
        if not h or not h.accepted:raise RuntimeError("G04B_GRIP_"+label+"_REJECTED")
        outcome=self.await_future(h.get_result_async(),label+"_RESULT",20,
                                  h.cancel_goal_async)
        data={"name":label,"command_m":q,"status":int(outcome.status),
              "result_error":int(outcome.result.error_code),
              "actual_m":self.joints[-1]["fingers"]}
        if data["status"]!=GoalStatus.STATUS_SUCCEEDED or data["result_error"]!=0:
            raise RuntimeError("G04B_GRIP_"+label+"_RESULT_FAILURE_"+str(data))
        if max(abs(data["actual_m"][n]-q) for n in FINGERS)>.003:
            raise RuntimeError("G04B_GRIP_"+label+"_ACTUAL_FINGER_ERROR")
        return data


def main():
    if os.environ.get("CH07_77_G04B_SIMULATION_ONLY_VERIFIED")!="YES":
        raise RuntimeError("G04B_ONLY_EXPLICIT_ACTIVE_GAZEBO_SIMULATION_ALLOWED")
    out=Path(os.environ["CH07_77_G04B_RECEIPT"])
    meta=json.loads(Path(os.environ["CH07_77_G04B_FIXTURE_RECEIPT"]).read_text())
    report={"scope":"G04B_REAL_GAZEBO_DYNAMIC_OBJECT_PHYSICAL_GRASP_LIFT_PLACE",
            "status":"FAIL","source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
            "fixture":meta,"g04a_old_live_xyz_replayed_as_current":False,
            "arm_goal_count":0,"finger_goal_count":0,
            "pose_snapshots":{},"arm_results":[],"finger_results":[],
            "contact_native_raw":"RECORDED_SEPARATELY_IN_ARTIFACT",
            "G05_integrated_live_perception":"NOT_RUN",
            "Ch10":"HOLD","hardware":"GAZEBO_SIMULATION_ONLY"}
    rclpy.init(args=["--ros-args","-p","use_sim_time:=true"])
    w=Witness()
    try:
        w.wait_ready()
        report["robot_joint_state_before"]=w.joints[-1]
        report["pose_snapshots"]["initial"]=rod_pose()
        assert math.dist(report["pose_snapshots"]["initial"],
                         meta["rod_center_initial_world_m"])<.045
        # First check that pre-grasp and grasp posture are genuine MoveIt
        # collision-free planner goals. The robot has not moved yet.
        for name,pose in (("pregrasp",[.50,0,1.85]),
                          ("grasp",[.62,0,1.85])):
            data=w.arm_goal(name+"_plan_only",pose,plan_only=True)
            report["arm_results"].append(data)
        report["finger_results"].append(w.grip_goal("open",.005))
        report["finger_goal_count"]+=1
        report["arm_results"].append(w.arm_goal("pregrasp",[.50,0,1.85]))
        report["arm_goal_count"]+=1
        report["pose_snapshots"]["pregrasp"]=rod_pose()
        report["arm_results"].append(w.arm_goal("approach",[.62,0,1.85]))
        report["arm_goal_count"]+=1
        report["pose_snapshots"]["approach"]=rod_pose()
        # Independent actual robot JointState -> original source FK, not
        # commanded joint targets or MoveGroup result pose. Preserve this
        # observation on failures to diagnose millimetre-scale grasp error.
        q=w.joints[-1]["arm"]
        rad=.5*math.sin(q["joint2"])+math.sin(q["joint2"]+q["joint3"])
        yaw=q["joint1"];tilt=q["joint2"]+q["joint3"]+q["joint_wrist"]
        wrist=[rad*math.cos(yaw),rad*math.sin(yaw),
               .6+.5*math.cos(q["joint2"])+math.cos(q["joint2"]+q["joint3"])]
        fingers_center=[
            wrist[0]+.1204*math.sin(tilt)*math.cos(yaw),
            wrist[1]+.1204*math.sin(tilt)*math.sin(yaw),
            wrist[2]+.1204*math.cos(tilt)]
        rod=report["pose_snapshots"]["approach"]
        report["actual_wrist_xyz_before_grip_m"]=wrist
        report["actual_fingertip_center_before_grip_m"]=fingers_center
        report["actual_rod_lateral_offset_before_grip_m"]=math.hypot(
            fingers_center[0]-rod[0],fingers_center[1]-rod[1])
        # Close just past the Ø24mm rod's two ideal contact faces. No
        # trajectory feedback/physics bypass. FJT may reject collision.
        report["finger_results"].append(w.grip_goal("contact_close",.011))
        report["finger_goal_count"]+=1
        w.spin_for(.65)
        report["pose_snapshots"]["closed"]=rod_pose()
        report["arm_results"].append(w.arm_goal("lift",[.48,0,1.96]))
        report["arm_goal_count"]+=1
        report["pose_snapshots"]["lift"]=rod_pose()
        report["lift_m"]=report["pose_snapshots"]["lift"][2]-report["pose_snapshots"]["initial"][2]
        assert report["lift_m"]>=.05, "G04B_OBJECT_DID_NOT_LIFT_WITH_GRIPPER"
        w.spin_for(1.3)
        report["pose_snapshots"]["held"]=rod_pose()
        hold=math.dist(report["pose_snapshots"]["held"],
                       report["pose_snapshots"]["lift"])
        report["object_pose_drift_during_hold_m"]=hold
        assert hold<=.025,"G04B_OBJECT_SLIPPED_WHILE_HELD"
        report["arm_results"].append(w.arm_goal("transfer",[.477,.217,1.759]))
        report["arm_goal_count"]+=1
        report["pose_snapshots"]["pre_release"]=rod_pose()
        report["finger_results"].append(w.grip_goal("release",.005))
        report["finger_goal_count"]+=1
        w.spin_for(2.0)
        report["pose_snapshots"]["settled"]=rod_pose()
        obj=report["pose_snapshots"]["settled"]
        report["placement_xy_error_m"]=math.hypot(obj[0]-.55,obj[1]-.25)
        report["placement_center_height_error_m"]=abs(obj[2]-1.85)
        assert report["placement_xy_error_m"]<=.09,"G04B_NOT_IN_DESTINATION_ROI"
        assert report["placement_center_height_error_m"]<=.055,"G04B_NOT_SETTLED_ON_BIN_SUPPORT"
        report["actual_joint_state_final"]=w.joints[-1]
        report["status"]="CANDIDATE_PASS_PENDING_INDEPENDENT_NATIVE_CONTACT_AUDIT"
        print("CH07_77_G04B_GAZEBO_OBJECT_LIFT_HOLD_PLACE_GEOMETRY_CANDIDATE_PASS_CONTACT_AUDIT_REQUIRED",flush=True)
    except Exception as exc:
        report["reason"]=repr(exc)
        print("CH07_77_G04B_FAIL "+repr(exc),flush=True)
        raise
    finally:
        report["joint_state_samples"]=len(w.joints)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        w.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=="__main__":
    main()
