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
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTrajectoryControllerState, JointTolerance
from ch07_181_arm_settle_contract import (
    assess_arm_settle, JOINT_GOAL_TOL_RAD, lower_bin_settle_recovery_eligible)
from ch07_181_symmetric_grasp_contract import symmetric_close_joint_target
from ch07_181_post_approach_settle_contract import measured_contact_settle_target, unchanged_collision_center
from ch07_181_physical_preload_contract import actual_preload_pass, EXPECTED_PRELOAD_M
from ch07_181_exact_fk import (original_finger_collision_center,
    original_finger_tool_z_axis,actual_tool_axis_angle_rad)
from ch07_181_bin_transport_contract import (corrected_high_target,
    exact_fk_high_bin_wrist_target,custody_offset,
    custody_drift,high_arrival_valid,feedback_centered_high_target,
    precise_high_arrival_valid,pre_release_valid,LOWER_WRIST_Z,
    historical_wrist_bias_lower_goal,actual_finger_tilt_drift,finger_tilt)
from ch07_181_native_recent_contact import (
    require_bilateral_pre_release_contact,require_bilateral_same_ecs_frame_force)
from ch07_181_high_goal_precision_contract import assess_precise_high_arrival
from ch07_181_jaw_axis_carry import (
    high_carry_jaw_compensation,real_jaw_world_axis_change,
    real_jaw_world_axis,MAX_ACTUAL_JAW_NORMAL_DRIFT_RAD,
    exact_world_jaw_lower_plan)
from ch07_181_reachable_release_waypoint import reachable_release_waypoint
from ch07_181_original_bin_safe_lower import collision_safe_lower_target
from ch07_181_release_wrist_retract import source_release_wrist_retract
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints,JointConstraint,MoveItErrorCodes,CollisionObject,PlanningScene
from moveit_msgs.srv import ApplyPlanningScene
from geometry_msgs.msg import Pose
from shape_msgs.msg import SolidPrimitive
from ch07_181_bin_moveit_scene_contract import exact_bin_collision_from_world
from ch07_181_collision_free_high_branch import alternative_high_elbow_target
from ch07_181_clearance_verified_high import source_bin_clearance_high_goal
from ch07_181_rotated_bin_high_goal import source_bin_rotated_high_goal
from trajectory_msgs.msg import JointTrajectoryPoint
from sensor_msgs.msg import JointState
from pal_statistics_msgs.msg import Statistics
from ch07_181_g04b_first_goal_causal_contract import first_goal_evidence

ARM=("joint1","joint2","joint3","joint4","joint_wrist")
FINGERS=("joint_finger1","joint_finger2")
POSE_RE=re.compile(r"Pose \[ XYZ \(m\) \] \[ RPY \(rad\) \]:\s*\n\s*\[\s*([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s*\]")

def rod_pose():
    res=subprocess.run(["gz","model","--model","g04_grasp_cylinder","--pose"],
                       capture_output=True,text=True,timeout=10,check=True)
    m=POSE_RE.search(res.stdout)
    if m is None: raise RuntimeError("G04B_NATIVE_GZ_ROD_POSE_UNPARSEABLE "+res.stdout[-500:])
    return [float(x) for x in m.groups()]


def native_robot_link_pose(link):
    """Independent Gazebo WORLD link pose, not reconstructed from JointState.

    gz model --link returns model, inertial-local link pose, and ACTUAL
    world link pose. Preserve world XYZ+RPY for collision geometry analysis.
    """
    if link not in ("finger1","finger2","link_wrist"):
        raise ValueError("G04B_UNEXPECTED_NATIVE_LINK")
    result=subprocess.run(["gz","model","--model","my_robot",
                           "--link",link,"--pose"],
                          capture_output=True,text=True,timeout=12,check=True)
    section=result.stdout.split("  - Link [",1)
    if len(section)!=2:
        raise RuntimeError("G04B_GAZEBO_LINK_POSE_MISSING_"+link)
    # Reuse the already-proven native Gazebo XYZ parser, then read the
    # immediately following RPY line. The matched second pose is the
    # link's WORLD pose (the first is its inertial-local offset).
    pattern=re.compile(
        POSE_RE.pattern +
        r"\s*\n\s*\[\s*([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s*\]"
    )
    poses=pattern.findall(section[1])
    # Each link lists its inertial relative pose first, then actual world.
    if len(poses)<2:raise RuntimeError("G04B_NATIVE_LINK_WORLD_POSE_UNPARSEABLE_"+link)
    values=list(map(float,poses[1]))
    return {"world_xyz_m":values[:3],"world_rpy_rad":values[3:],
            "raw_link_name":link}


def arm_ik_tilted_fingers(x,y,z):
    """Original 2R position IK, with opposing fingers along world Y.

    Original joint4 turns about link3 local Z. q4=pi/2 rotates original
    prismatic closure axis into world Y while preserving the tool's
    forward-projecting length direction; q5=0. No 6D IK success claimed.
    """
    radius=math.hypot(x,y);dz=z-.6;a=.5;b=1.
    c=(radius**2+dz**2-a*a-b*b)/(2*a*b)
    if not math.isfinite(c) or abs(c)>1:raise ValueError("G04B_UNREACHABLE_WRIST")
    q3=math.acos(c)
    q2=math.atan2(radius,dz)-math.atan2(b*math.sin(q3),a+b*math.cos(q3))
    # Source collision wrist extends local z<=.06, fingers local z=.06..14.
    # The dynamic rod must enter between fingers at local z≈.12, never
    # into the wrist box. Tool tilt is the G04B geometry receipt .72rad.
    target=dict(zip(ARM,[math.atan2(y,x),q2,q3,math.pi/2,0.]))
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


def measured_finger_center(arm):
    """Exact original URDF Rz(q1) Ry(q2+q3) Rz(q4) Ry(qw) finger centre.

    The old sin(q2+q3+qwrist) was INVALID at q4≈pi/2 and falsely
    advertised that yaw/pitch compensation preserved tool orientation.
    """
    return original_finger_collision_center(arm)


class Witness(Node):
    def __init__(self):
        super().__init__("ch07_77_g04b_actual_gazebo_contact_witness")
        self.move=ActionClient(self,MoveGroup,"/move_action")
        self.bin_scene_client=self.create_client(ApplyPlanningScene,"/apply_planning_scene")
        self.arm_direct=ActionClient(self,FollowJointTrajectory,
                                     "/arm_group_controller/follow_joint_trajectory")
        self.grip=ActionClient(self,FollowJointTrajectory,
                               "/gripper_group_controller/follow_joint_trajectory")
        self.joints=[]
        self.last_grip_data=None
        self.controller_samples=[]
        self.arm_joint2_controller_samples=[]
        self.arm_joint2_observer_errors=[]
        self.last_arm_settle_data=None
        self.last_high_joint2_causal=None
        self.last_lower_joint3_causal=None
        self.hardware_introspection_samples=[]
        self.hardware_introspection_errors=[]
        # Existing Jazzy publisher is BEST_EFFORT (Issue #181 CI #43591101353).
        # This is a read-only diagnostic subscriber; no command path changes.
        self.create_subscription(Statistics,
            '/controller_manager/introspection_data/full',
            self.on_hardware_introspection,
            QoSProfile(depth=10,reliability=ReliabilityPolicy.BEST_EFFORT))
        self.create_subscription(JointTrajectoryControllerState,
            "/gripper_group_controller/controller_state",
            self.on_controller_state,10)
        self.create_subscription(JointTrajectoryControllerState,
            "/arm_group_controller/controller_state",
            self.on_arm_joint2_controller_state,10)
        self.create_subscription(JointState,"/joint_states",self.on_state,10)

    def on_hardware_introspection(self,msg):
        try:
            values={}
            for stat in msg.statistics:
                name=str(getattr(stat,'name',''))
                if not any(n in name for n in (*FINGERS,"joint2","joint3")):
                    continue
                value=float(getattr(stat,'value'))
                if math.isfinite(value):values[name]=value
            if values:
                sim_now=self.get_clock().now().nanoseconds/1e9
                self.hardware_introspection_samples.append({
                    'sim_observed_s':sim_now,
                    'source_stamp':msg.header.stamp.sec+
                                   msg.header.stamp.nanosec*1e-9,
                    'values':values})
                self.hardware_introspection_samples=self.hardware_introspection_samples[-4500:]
        except Exception as exc:
            self.hardware_introspection_errors.append(repr(exc))

    def on_controller_state(self,m):
        # control_msgs Jazzy exposes the desired command and actual
        # controller-tracked positions; save independent of FJT status.
        names=list(m.joint_names)
        # Jazzy JointTrajectoryControllerState names are reference/feedback/error.
        # G04B original #43574030542 stored [] for obsolete desired/actual.
        reference=getattr(m,"reference",None)
        feedback=getattr(m,"feedback",None)
        err=getattr(m,"error",None)
        stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
        record={
            "stamp":stamp, "names":names,
            "reference":list(getattr(reference,"positions",[])),
            "feedback":list(getattr(feedback,"positions",[])),
            "error":list(getattr(err,"positions",[]))
        }
        if (names!=list(FINGERS) or
            any(len(record[key])!=2 or not all(math.isfinite(v) for v in record[key])
                for key in ("reference","feedback","error"))):
            raise RuntimeError("G04B_JAZZY_JTC_REFERENCE_FEEDBACK_ERROR_MISSING")
        self.controller_samples.append(record)
        # Preserve the WHOLE 2s FJT+2s tolerance window. The previous 100
        # samples showed only the post-ABORT reference reset to actual.
        self.controller_samples=self.controller_samples[-1500:]

    def on_arm_joint2_controller_state(self,m):
        # Read-only per-sim-step Jazzy arm JTC actual feedback, NOT a Goal.
        try:
            names=list(m.joint_names)
            if set(names)!=set(ARM):return
            indices={"joint2":names.index("joint2"),"joint3":names.index("joint3")}
            record={"stamp":m.header.stamp.sec+m.header.stamp.nanosec*1e-9}
            for field in ("reference","feedback","error"):
                values=list(getattr(getattr(m,field,None),"positions",[]))
                if len(values)!=len(names) or not all(math.isfinite(v) for v in values):
                    raise ValueError("ARM_JTC_"+field+"_INVALID")
                for joint,idx in indices.items():
                    record[field+"_"+joint+"_rad"]=float(values[idx])
            self.arm_joint2_controller_samples.append(record)
            self.arm_joint2_controller_samples=self.arm_joint2_controller_samples[-3000:]
        except Exception as exc:
            self.arm_joint2_observer_errors.append(repr(exc))

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

    def register_real_bin_planning_collision(self,world_path):
        """One-factor change: MoveIt uses the SAME native static Gazebo bin."""
        spec=exact_bin_collision_from_world(
            world_path,allow_cycle12_yaw=(os.environ.get("CH07_181_C12_BIN_YAW_ONLY")=="YES"))
        if not self.bin_scene_client.wait_for_service(timeout_sec=12.):
            raise RuntimeError("G04B_C08_APPLY_PLANNING_SCENE_SERVER_MISSING")
        scene=PlanningScene()
        scene.is_diff=True
        obj=CollisionObject()
        obj.header.frame_id=spec["frame_id"]
        obj.id=spec["id"]
        primitive=SolidPrimitive()
        primitive.type=SolidPrimitive.BOX
        primitive.dimensions=list(spec["box_m"])
        origin=Pose()
        origin.position.x,origin.position.y,origin.position.z=spec["center_m"]
        origin.orientation.z=spec["quaternion_xyzw"][2]
        origin.orientation.w=spec["quaternion_xyzw"][3]
        obj.primitives=[primitive]
        obj.primitive_poses=[origin]
        obj.operation=CollisionObject.ADD
        scene.world.collision_objects=[obj]
        request=ApplyPlanningScene.Request()
        request.scene=scene
        response=self.await_future(self.bin_scene_client.call_async(request),
                                   "C08_APPLY_BIN_SCENE",15)
        if response is None or not response.success:
            raise RuntimeError("G04B_C08_MOVEIT_BIN_COLLISION_APPLY_FAILED")
        return {**spec,"apply_planning_scene_success":True,
                "actual_gazebo_world_mutated":False,
                "acceptance":"STILL_BLOCKED_PENDING_NATIVE_PHYSICS"}

    def arm_goal(self,label,xyz,plan_only=False,joint_override=None,
                 defer_lower_fjt_recovery=False):
        # Avoid reconstructing a different elbow/wrist posture when moving
        # laterally toward the rod. For a yaw-only sweep, retain the ACTUAL
        # observed radial geometry, rather than re-solving approximate IK.
        target=({n:float(joint_override[n]) for n in ARM}
                if joint_override is not None else arm_ik_tilted_fingers(*xyz))
        assert set(target)==set(ARM) and all(math.isfinite(v) for v in target.values())
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
            # A 35 mrad goal tolerance is > 10mm rod/finger radial clearance.
            # Keep the broad tolerance for already validated coarse moves,
            # use 2 mrad only for precise yaw or contact alignment.
            tolerance=.002 if joint_override is not None else .035
            jc.tolerance_above=tolerance
            jc.tolerance_below=tolerance
            jc.weight=1.
            c.joint_constraints.append(jc)
        goal.request.goal_constraints.append(c)
        before=self.joints[-1] if self.joints else {}
        high_first_sim_s=(before.get("stamp",0.) if label=="transfer_high_above_bin" else None)
        lower_first_sim_s=(before.get("stamp",0.) if label=="lower_into_bin" else None)
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
        if label=="transfer_high_above_bin":
            # Preserve real high MoveGroup JTC/HW evidence before any later
            # acceptance exception. Command interface names are not guessed:
            # record actual introspection names and timed samples.
            high_end_s=self.joints[-1]["stamp"] if self.joints else high_first_sim_s
            a=[s for s in self.arm_joint2_controller_samples
               if high_first_sim_s<=s["stamp"]<=high_end_s]
            h=[s for s in self.hardware_introspection_samples
               if high_first_sim_s<=s["sim_observed_s"]<=high_end_s]
            named=[{"stamp":s["sim_observed_s"],"name":name,"position_rad":float(value)}
                   for s in h for name,value in s["values"].items()
                   if "joint2" in name and "command" in name.lower()
                   and "position" in name.lower()]
            causal={"start_sim_s":high_first_sim_s,"end_sim_s":high_end_s,
                    "joint":"joint2",
                    "jtc_reference_feedback_error":a,
                    "hardware_command_position":named,
                    "introspection_joint2_names":sorted(set(
                        name for s in h for name in s["values"] if "joint2" in name)),
                    "observer_errors":self.arm_joint2_observer_errors[-10:],
                    "trace_csv":"gazebo_finger_ecs_pre_post_command.csv",
                    "scope":"HIGH_MOVEGROUP_READ_ONLY_NOT_PHYSICAL_PASS"}
            row["high_joint2_causal_evidence"]=causal
            self.last_high_joint2_causal=causal
        if label=="lower_into_bin":
            # Cycle 04: preserve native lower-stage provenance BEFORE FJT
            # recovery and BEFORE any error can short-circuit the receipt.
            lower_end_s=self.joints[-1]["stamp"] if self.joints else lower_first_sim_s
            jtc=[v for v in self.arm_joint2_controller_samples
                 if lower_first_sim_s<=v["stamp"]<=lower_end_s]
            hw=[{"stamp":v["sim_observed_s"],"name":"command_interface.joint3/position",
                 "position_rad":v["values"]["command_interface.joint3/position"]}
                for v in self.hardware_introspection_samples
                if lower_first_sim_s<=v["sim_observed_s"]<=lower_end_s
                and "command_interface.joint3/position" in v["values"]]
            self.last_lower_joint3_causal={
                "stage":"lower_into_bin_MoveGroup",
                "start_sim_s":lower_first_sim_s,"end_sim_s":lower_end_s,
                "goal_joint3_rad":target["joint3"],
                "actual_joint3_rad":self.joints[-1]["arm"]["joint3"],
                "jtc_reference_feedback_error":jtc,
                "hardware_command_position":hw,
                "observer_errors":self.arm_joint2_observer_errors[-10:],
                "native_trace_csv":"gazebo_finger_ecs_pre_post_command.csv",
                "scope":"READ_ONLY_G04B_BLOCKED"}
            row["lower_joint3_causal_evidence"]=self.last_lower_joint3_causal
        if (row["action_status"]!=GoalStatus.STATUS_SUCCEEDED or
            row["moveit_error"]!=MoveItErrorCodes.SUCCESS or
            row["planned_points"]==0):
            raise RuntimeError("G04B_ARM_"+label+"_NOT_SUCCEEDED_"+str(row))
        if not plan_only:
            errors={n:abs(self.joints[-1]["arm"][n]-target[n]) for n in ARM}
            row["measured_joint_errors_rad"]=errors
            if max(errors.values())>.075:
                # The lower_into_bin MoveGroup can falsely report SUCCEEDED
                # while real q3 is 135mrad behind (#43712237998). For that
                # ONE stage only, return an explicitly pending strict FJT
                # request; NEVER mark this as joint tracking PASS. The
                # caller must perform the independent <=10mrad real feedback
                # gate before release; huge errors still raise immediately.
                if (defer_lower_fjt_recovery and
                        lower_bin_settle_recovery_eligible(label,errors)):
                    row["strict_joint_feedback_deferred_to_fjt"]=True
                else:
                    raise RuntimeError("G04B_ARM_"+label+"_JOINT_ERROR_EXCESS_"+str(errors))
        return row

    def arm_precision_settle(self,target):
        """One direct FJT after successful REAL MoveGroup; Issue #181 bounded remedy."""
        if set(target)!=set(ARM) or not all(math.isfinite(v) for v in target.values()):
            raise ValueError("G04B_181_ARM_SETTLE_INVALID_TARGET")
        if not self.arm_direct.wait_for_server(timeout_sec=8.):
            raise RuntimeError("G04B_181_ARM_FJT_SERVER_NOT_READY")
        goal=FollowJointTrajectory.Goal()
        goal.trajectory.joint_names=list(ARM)
        point=JointTrajectoryPoint()
        point.positions=[float(target[n]) for n in ARM]
        point.time_from_start.sec=3
        goal.trajectory.points=[point]
        for n in ARM:
            jt=JointTolerance()
            jt.name=n
            jt.position=JOINT_GOAL_TOL_RAD
            goal.goal_tolerance.append(jt)
        goal.goal_time_tolerance.sec=2
        arm_fjt_start_sim=self.joints[-1]["stamp"] if self.joints else 0.
        handle=self.await_future(self.arm_direct.send_goal_async(goal),
                                 "post_movegroup_settle_ACCEPT",12)
        if not handle or not handle.accepted:
            raise RuntimeError("G04B_181_ARM_FJT_SETTLE_REJECTED")
        outcome=self.await_future(handle.get_result_async(),
                                  "post_movegroup_settle_RESULT",15,
                                  handle.cancel_goal_async)
        observed=dict(self.joints[-1]["arm"])
        verdict,errors=assess_arm_settle(int(outcome.status),
                                         int(outcome.result.error_code),
                                         target,observed)
        arm_fjt_end_sim=self.joints[-1]["stamp"] if self.joints else arm_fjt_start_sim
        arm_jtc_window=[s for s in self.arm_joint2_controller_samples
                        if arm_fjt_start_sim<=s["stamp"]<=arm_fjt_end_sim]
        hw_window=[s for s in self.hardware_introspection_samples
                   if arm_fjt_start_sim<=s["sim_observed_s"]<=arm_fjt_end_sim
                   and "command_interface.joint2/position" in s["values"]]
        arm_jtc3=[v for v in self.arm_joint2_controller_samples
                  if arm_fjt_start_sim<=v["stamp"]<=arm_fjt_end_sim]
        hw3=[{"stamp":v["sim_observed_s"],"name":"command_interface.joint3/position",
              "position_rad":v["values"]["command_interface.joint3/position"]}
             for v in self.hardware_introspection_samples
             if arm_fjt_start_sim<=v["sim_observed_s"]<=arm_fjt_end_sim
             and "command_interface.joint3/position" in v["values"]]
        row={"name":"post_movegroup_direct_fjt_arm_settle",
             "desired":target,"actual":observed,"error_rad":errors,
             "action_status":int(outcome.status),
             "result_error":int(outcome.result.error_code),
             "goal_tolerance_rad":JOINT_GOAL_TOL_RAD,
             "goal_time_tolerance_s":2,"verdict":verdict,
             "joint3_observation_window":{
                 "stage":"lower_into_bin_direct_FJT_if_called",
                 "start_sim_s":arm_fjt_start_sim,"end_sim_s":arm_fjt_end_sim,
                 "goal_joint3_rad":target["joint3"],
                 "actual_joint3_rad":observed["joint3"],
                 "jtc_reference_feedback_error":arm_jtc3,
                 "hardware_command_position":hw3,
                 "observer_errors":self.arm_joint2_observer_errors[-10:],
                 "native_trace_csv":"gazebo_finger_ecs_pre_post_command.csv",
                 "scope":"READ_ONLY_G04B_BLOCKED"},
             "joint2_observation_window":{
                 "start_sim_s":arm_fjt_start_sim,
                 "end_sim_s":arm_fjt_end_sim,
                 "jtc_reference_feedback_error":arm_jtc_window,
                 "hardware_command_position":[
                    {"stamp":s["sim_observed_s"],
                     "value_rad":s["values"]["command_interface.joint2/position"]}
                    for s in hw_window],
                 "observer_errors":self.arm_joint2_observer_errors[-10:],
                 "native_trace_csv":"gazebo_finger_ecs_pre_post_command.csv",
                 "status":"READ_ONLY_NOT_PHYSICAL_PASS"}}
        self.last_arm_settle_data=row
        if verdict!="ARM_SETTLE_SCOPED_PASS":
            raise RuntimeError("G04B_181_ARM_SETTLE_FAILED_"+str(row))
        return row

    def release_and_retract_fjt(self,arm_target):
        """Both real Jazzy FJT servers act concurrently, no fabricated pose.

        This one C18 action replaces only the blocking release call. All
        original independent release-contact, zero-wrist-rod and settled ROI
        acceptance checks run exactly as before.
        """
        if not self.arm_direct.wait_for_server(timeout_sec=8.):
            raise RuntimeError("C18_ARM_DIRECT_ACTION_MISSING")
        if not self.grip.wait_for_server(timeout_sec=8.):
            raise RuntimeError("C18_GRIPPER_DIRECT_ACTION_MISSING")
        start=dict(self.joints[-1]["arm"])
        if (set(arm_target)!=set(ARM) or
            any(not math.isfinite(v) for v in arm_target.values()) or
            abs(arm_target["joint3"]-start["joint3"]+.055)>.012 or
            any(abs(arm_target[n]-start[n])>.012 for n in ARM if n!="joint3")):
            raise ValueError("C18_RETREAT_TARGET_NOT_ONLY_BOUNDED_JOINT3")
        sim_start=self.joints[-1]["stamp"]
        ag=FollowJointTrajectory.Goal()
        ag.trajectory.joint_names=list(ARM)
        ap=JointTrajectoryPoint()
        ap.positions=[float(arm_target[n]) for n in ARM]
        ap.time_from_start.nanosec=800000000
        ag.trajectory.points=[ap]
        for n in ARM:
            tol=JointTolerance();tol.name=n;tol.position=.01
            ag.goal_tolerance.append(tol)
        ag.goal_time_tolerance.sec=2
        gg=FollowJointTrajectory.Goal()
        gg.trajectory.joint_names=list(FINGERS)
        gp=JointTrajectoryPoint()
        gp.positions=[0.0,0.0]
        gp.time_from_start.sec=2
        gg.trajectory.points=[gp]
        for n in FINGERS:
            tol=JointTolerance();tol.name=n;tol.position=.001
            gg.goal_tolerance.append(tol)
        gg.goal_time_tolerance.sec=2
        # Both independent controller Goals are enqueued before either result
        # is awaited; the original blocking release was TOO LATE for retreat.
        af=self.arm_direct.send_goal_async(ag)
        gf=self.grip.send_goal_async(gg)
        ah=self.await_future(af,"C18_ARM_RETRACT_ACCEPT",12)
        gh=self.await_future(gf,"C18_GRIP_RELEASE_ACCEPT",12)
        if not ah or not ah.accepted or not gh or not gh.accepted:
            if ah and ah.accepted:ah.cancel_goal_async()
            if gh and gh.accepted:gh.cancel_goal_async()
            raise RuntimeError("C18_RELEASE_RETRACT_ACTION_NOT_ACCEPTED")
        aresult=self.await_future(ah.get_result_async(),"C18_ARM_RETRACT_RESULT",
                                  20,ah.cancel_goal_async)
        gresult=self.await_future(gh.get_result_async(),"C18_RELEASE_RESULT",
                                  20,gh.cancel_goal_async)
        arm_actual=dict(self.joints[-1]["arm"])
        finger_actual=dict(self.joints[-1]["fingers"])
        errors={n:abs(arm_actual[n]-arm_target[n]) for n in ARM}
        grip_error={n:abs(finger_actual[n]) for n in FINGERS}
        arm_row={
            "name":"release_retract_from_rod",
            "target_joint_positions":dict(arm_target),
            "source_actual_joint_positions":start,
            "actual_joint_positions":arm_actual,
            "measured_joint_errors_rad":errors,
            "action_status":int(aresult.status),
            "result_error":int(aresult.result.error_code),
            "goal_time_from_start_s":.8,
            "started_sim_s":sim_start,
            "finished_sim_s":self.joints[-1]["stamp"],
            "coordinated_direct_controller_fjt_no_fake_physics":True}
        grip_row={
            "name":"release","command_m":0.0,
            "command_by_joint_m":{n:0.0 for n in FINGERS},
            "status":int(gresult.status),
            "result_error":int(gresult.result.error_code),
            "explicit_fjt_goal_tolerance_m":.001,
            "explicit_fjt_goal_time_tolerance_sec":2,
            "actual_m":finger_actual,
            "per_finger_position_error_m":finger_actual,
            "tracking_error_max_m":max(grip_error.values()),
            "joint_tracking_pass":max(grip_error.values())<=.001,
            "controller_state_last":(
                self.controller_samples[-1] if self.controller_samples else None),
            "controller_state_sample_count":len(self.controller_samples),
            "diagnostic_free_space":False,
            "contact_close_position_not_success_criterion":False,
            "simultaneous_arm_retract":True}
        self.last_grip_data=grip_row
        if (arm_row["action_status"]!=GoalStatus.STATUS_SUCCEEDED or
            arm_row["result_error"]!=0 or max(errors.values())>.01 or
            grip_row["status"]!=GoalStatus.STATUS_SUCCEEDED or
            grip_row["result_error"]!=0 or not grip_row["joint_tracking_pass"]):
            raise RuntimeError("C18_ACTUAL_RELEASE_RETRACT_FJT_OR_FEEDBACK_FAILED")
        return grip_row,arm_row

    def grip_goal(self,label,q,q2=None,diagnostic=False):
        # Both original ROS 2 joints must always be present. A diagnostic
        # may set asymmetric desired positions to isolate real actuation,
        # but cannot bypass original joint limits or success provenance.
        if q2 is None:
            q2=q
        desired=dict(zip(FINGERS,(float(q),float(q2))))
        if not all(0.0<=value<=.025 for value in desired.values()):
            raise ValueError("G04B_GRIPPER_LIMIT")
        goal=FollowJointTrajectory.Goal()
        goal.trajectory.joint_names=list(FINGERS)
        pt=JointTrajectoryPoint()
        pt.positions=[float(q),float(q2)]
        pt.time_from_start.sec=2
        goal.trajectory.points=[pt]
        # A FollowJointTrajectory SUCCEEDED without explicit goal tolerance
        # concealed a 12 mm finger2 error in the original CI #43574030542.
        # Contact closure is allowed 2.5 mm of *physical* stopping margin;
        # true grasp still requires independent bilateral native forces,
        # real Gazebo world-Z lift, hold, release and pose witness.
        tolerance_m=.0025 if label=="contact_close" else .001
        for name in FINGERS:
            tol=JointTolerance()
            tol.name=name
            tol.position=tolerance_m
            goal.goal_tolerance.append(tol)
        goal.goal_time_tolerance.sec=2
        goal_start_sim=self.joints[-1]['stamp'] if self.joints else 0.0
        h=self.await_future(self.grip.send_goal_async(goal),label+"_ACCEPT",15)
        if not h or not h.accepted:
            raise RuntimeError("G04B_GRIP_"+label+"_REJECTED")
        outcome=self.await_future(h.get_result_async(),label+"_RESULT",20,
                                  h.cancel_goal_async)
        actual=dict(self.joints[-1]["fingers"])
        delta={n:float(actual[n]-desired[n]) for n in FINGERS}
        data={"name":label,"command_m":q,
              "command_by_joint_m":desired,
              "status":int(outcome.status),
              "result_error":int(outcome.result.error_code),
              "explicit_fjt_goal_tolerance_m":tolerance_m,
              "explicit_fjt_goal_time_tolerance_sec":2,
              "actual_m":actual,
              "per_finger_position_error_m":delta,
              "tracking_error_max_m":max(abs(v) for v in delta.values()),
              "joint_tracking_pass":max(abs(v) for v in delta.values())<=.001,
              "controller_state_last":(
                  self.controller_samples[-1] if self.controller_samples else None
              ),
              "controller_state_sample_count":len(self.controller_samples),
              "diagnostic_free_space":bool(diagnostic),
              "contact_close_position_not_success_criterion":(
                  label=="contact_close")}
        if label=='lower_stop_release_both_fingers_2mm':
            goal_end_sim=self.joints[-1]['stamp'] if self.joints else goal_start_sim
            data['first_goal_causal_receipt']=first_goal_evidence(
                self.controller_samples,self.hardware_introspection_samples,
                actual,goal_start_sim,goal_end_sim,
                target_m=EXPECTED_PRELOAD_M)
            data['introspection_schema_errors']=self.hardware_introspection_errors[-15:]
            data['causal_receipt_is_not_physical_acceptance']=True
        self.last_grip_data=data
        if data["status"]!=GoalStatus.STATUS_SUCCEEDED or data["result_error"]!=0:
            raise RuntimeError("G04B_GRIP_"+label+"_RESULT_FAILURE_"+str(data))
        # The pre-contact diagnostic records both commanded and measured
        # joints even if a finger freezes; don't approach the physical rod
        # until the independent post-diagnostic acceptance below.
        if not diagnostic and label!="contact_close" and not data["joint_tracking_pass"]:
            raise RuntimeError("G04B_GRIP_"+label+"_ACTUAL_FINGER_ERROR")
        if label=="contact_close":
            assert all(-1e-6<=actual[n]<=.025001 for n in FINGERS),(
                "G04B_CONTACT_ACTUAL_JOINT_LIMIT_VIOLATED_"+str(data))
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
            "finger_clearance_preflight":"NOT_RUN",
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
        assert meta["height_m"]==.08 and meta["rod_min_local_z_m"]>=.065,(
            "G04B_SOURCE_GEOMETRY_WRIST_CLEARANCE_PREFLIGHT_FAILED")
        # G04B corrected axial grasp: original q4 controls finger
        # separation (NOT the wrist pitch). At q4=+pi/2, the two finger
        # collision faces oppose one another along world Y at equal Z.
        # Approach the rod along X, not by sweeping a finger across Y.
        pregrasp=(.49,0.,1.85)
        stage=(.56,0.,1.85)
        grasp=(.63,0.,1.85)
        for name,xyz in (("pregrasp",pregrasp),("grasp",grasp)):
            report["arm_results"].append(
                w.arm_goal(name+"_plan_only",xyz,plan_only=True))
        report["finger_results"].append(w.grip_goal("open",0.0))
        report["finger_goal_count"]+=1
        # Original real CI #43599142218: finger2 at physical 2mm then
        # 11mm PASS, but finger1 left at q0 FROZE (0mm for 11mm Goal,
        # FJT ABORTED). Thus BOTH original prismatic joints need one
        # real measured 2mm release before the same MoveGroup arm motion.
        # No fake attach/teleport, increased effort or tolerance relaxation.
        preload=w.grip_goal("lower_stop_release_both_fingers_2mm",
                            EXPECTED_PRELOAD_M,EXPECTED_PRELOAD_M,diagnostic=True)
        report["finger_results"].append(preload)
        report["finger_goal_count"]+=1
        report["lower_stop_release_both_fingers_pre_movegroup"]=preload
        if any(abs(preload["actual_m"][name]-EXPECTED_PRELOAD_M)>.0005
               for name in FINGERS):
            raise RuntimeError("G04B_181_BOTH_REAL_FINGERS_2MM_NOT_REACHED")
        nominal_pregrasp=arm_ik_tilted_fingers(*pregrasp)
        report["arm_results"].append(
            w.arm_goal("pregrasp",pregrasp,joint_override=nominal_pregrasp))
        report["arm_goal_count"]+=1
        # CI #43584052832: MoveGroup-only led to frozen finger with reference
        # 12mm; one DIRECT arm FJT settle restored actual bilateral control.
        # Preserve original MoveGroup planned+executed motion and independent
        # contact/lift/hold/place witness; no force/attach/teleport.
        report["post_movegroup_arm_settle"]=w.arm_precision_settle(nominal_pregrasp)
        report["arm_results"].append(report["post_movegroup_arm_settle"])
        report["arm_goal_count"]+=1
        report["lower_stop_release_after_pregrasp_actual_m"]=dict(
            w.joints[-1]["fingers"])
        if any(abs(report["lower_stop_release_after_pregrasp_actual_m"][name]
                   -EXPECTED_PRELOAD_M)>.0005 for name in FINGERS):
            raise RuntimeError("G04B_181_BILATERAL_PRELOAD_LOST_AFTER_PREGRASP")
        report["pose_snapshots"]["pregrasp"]=rod_pose()
        assert math.dist(report["pose_snapshots"]["pregrasp"],
                         report["pose_snapshots"]["initial"])<=.008,(
            "G04B_ROD_DISTURBED_BEFORE_APPROACH")
        # The seven original unloaded finger tests are already independently
        # accepted in public #43584052832 and #43584676926. They previously
        # reopened finger2 to the hard limit q=0, undoing the diagnosed 2mm
        # release. Do NOT rerun them in the real grasp session or fake PASS.
        report["finger_clearance_preflight"]=[]
        report["free_space_diagnostics_status"]="NOT_RERUN_PRIOR_PUBLIC_SCOPED_EVIDENCE"
        report["prior_free_space_ci_runs"]=[43584052832,43584676926,43595476665]
        report["lower_stop_release_after_pregrasp_joint_state"]=w.joints[-1]["fingers"]
        assert math.dist(rod_pose(),report["pose_snapshots"]["initial"])<=.008
        report["precontact_alignment"]=[]
        report["radial_refinements"]=[]
        start_tip=measured_finger_center(w.joints[-1]["arm"])
        report["precontact_alignment"].append({
            "name":"pregrasp","actual_collision_center_xyz":start_tip})
        assert .49<=start_tip[0]<=.62 and abs(start_tip[1])<=.02,(
            "G04B_PREGRASP_NOT_BEHIND_ROD_NO_APPROACH")
        report["arm_results"].append(w.arm_goal(
            "x_approach_clearance_stage",stage,
            joint_override=arm_ik_tilted_fingers(*stage)))
        report["arm_goal_count"]+=1
        report["pose_snapshots"]["x_clearance_stage"]=rod_pose()
        assert math.dist(report["pose_snapshots"]["x_clearance_stage"],
                         report["pose_snapshots"]["initial"])<=.012,(
            "G04B_ROD_MOVED_BEFORE_X_INSERTION_NO_CLOSE")
        stage_tip=measured_finger_center(w.joints[-1]["arm"])
        report["precontact_alignment"].append({
            "name":"x_approach_clearance_stage","actual_collision_center_xyz":stage_tip})
        assert stage_tip[0]<.665 and abs(stage_tip[1])<=.016,(
            "G04B_STAGE_NOT_CLEAR_OF_ROD_NO_CLOSE")
        report["arm_results"].append(w.arm_goal(
            "x_approach_insertion",grasp,
            joint_override=arm_ik_tilted_fingers(*grasp)))
        report["arm_goal_count"]+=1
        report["pose_snapshots"]["approach"]=rod_pose()
        report["preclose_object_shift_m"]=math.dist(
            report["pose_snapshots"]["approach"],
            report["pose_snapshots"]["initial"])
        if report["preclose_object_shift_m"]>.018:
            raise RuntimeError("G04B_ROD_DISTURBED_DURING_X_INSERTION_NO_CLOSE")
        q=w.joints[-1]["arm"]
        collision_center=measured_finger_center(q)
        report["precision_contact_center_feedback"]=[]
        # Actual Gazebo arm final state can differ by 5-7mm from the
        # declared MoveGroup goal despite a SUCCEEDED Action. Correct
        # only a few milliradians, with both fingers OPEN and already
        # correctly opposed in Y. Do not relax 5mm independent audit.
        for refinement in range(2):
            error_x=.70-collision_center[0]
            report["precision_contact_center_feedback"].append({
                "step":refinement,"observed_xyz":collision_center,
                "error_x_m":error_x})
            if abs(error_x)<=.004:break
            assert abs(error_x)<=.015, "G04B_FINE_ALIGNMENT_TOO_LARGE_NO_CLOSE"
            theta=q["joint2"]+q["joint3"]
            dx_dq2=.5*math.cos(q["joint2"])+math.cos(theta)+.10*math.cos(theta)
            assert dx_dq2>.6,"G04B_FINE_ALIGNMENT_JACOBIAN_INVALID"
            delta=max(-.010,min(.010,error_x/dx_dq2))
            fine=dict(q)
            fine["joint2"]+=delta
            assert -1.57079<fine["joint2"]<1.57079
            report["arm_results"].append(w.arm_goal(
                "fine_x_alignment_"+str(refinement),None,joint_override=fine))
            report["arm_goal_count"]+=1
            w.spin_for(.3)
            q=dict(w.joints[-1]["arm"])
            collision_center=measured_finger_center(q)
            current_pose=rod_pose()
            assert math.dist(current_pose,report["pose_snapshots"]["initial"])<=.018,(
                "G04B_ROD_MOVED_DURING_FINE_ALIGNMENT_NO_CLOSE")
            report["pose_snapshots"]["approach"]=current_pose
        report["actual_fingertip_center_before_grip_m"]=collision_center
        report["aligned_pregrasp_tip_xyz"]=collision_center
        report["aligned_pregrasp_radius_error_m"]=abs(collision_center[0]-.70)
        report["aligned_pregrasp_x_error_m"]=abs(collision_center[0]-.70)
        report["radial_refinements"].append({
            "method":"PREVALIDATED_DIRECT_MOVEGROUP_PRECISE_JOINT_TARGET",
            "actual_collision_center_xyz":collision_center})
        assert abs(collision_center[0]-.70)<=.008 and abs(collision_center[1])<=.01,(
            "G04B_CONTACT_CENTRE_NOT_ALIGNED_NO_CLOSE")
        assert abs(q["joint4"]-math.pi/2)<=.005 and abs(q["joint_wrist"])<=.005,(
            "G04B_OPPOSING_FINGER_AXIS_NOT_WORLD_Y_NO_CLOSE")
        # CI #43586210350: after MoveGroup precise approach, finger2 11mm
        # reference did not produce any real displacement or native contact.
        # The earlier post-MoveGroup DIRECT FJT arm settle fixed an identical
        # motor freeze at PREGRASP. Apply the SAME single bounded controller
        # transition after FINAL MoveGroup alignment, with the ACTUAL arm
        # state as target. This must not change robot/grasp geometry.
        before_contact_settle_center=measured_finger_center(q)
        contact_target=measured_contact_settle_target(dict(q))
        report["post_final_approach_arm_settle"]=w.arm_precision_settle(contact_target)
        report["arm_results"].append(report["post_final_approach_arm_settle"])
        report["arm_goal_count"]+=1
        report["lower_stop_release_before_contact_actual_m"]=dict(
            w.joints[-1]["fingers"])
        report["lower_stop_release_real_actual_pass"]=actual_preload_pass(
            report["lower_stop_release_both_fingers_pre_movegroup"],
            report["lower_stop_release_after_pregrasp_actual_m"],
            report["lower_stop_release_before_contact_actual_m"])
        if not report["lower_stop_release_real_actual_pass"]:
            raise RuntimeError("G04B_181_PRELOAD_LOST_BEFORE_PHYSICAL_CONTACT")
        settled_arm=dict(w.joints[-1]["arm"])
        after_contact_settle_center=measured_finger_center(settled_arm)
        report["post_final_approach_contact_centers_m"]={
            "before":before_contact_settle_center,"after":after_contact_settle_center}
        assert unchanged_collision_center(before_contact_settle_center,
                                          after_contact_settle_center),(
            "G04B_181_POST_APPROACH_SETTLE_UNINTENDED_TOOL_MOTION")
        assert math.dist(rod_pose(),report["pose_snapshots"]["initial"])<=.018,(
            "G04B_181_POST_APPROACH_SETTLE_ROD_MOVED_BEFORE_CLOSE")
        report["pose_snapshots"]["yaw_stage"]=report["pose_snapshots"]["x_clearance_stage"]
        report["rod_shift_before_close_at_yaw_stage_m"]=math.dist(
            report["pose_snapshots"]["yaw_stage"],
            report["pose_snapshots"]["initial"])
        report["pose_snapshots"]["aligned_pregrasp"]=report["pose_snapshots"]["pregrasp"]
        report["approach_axis"]="WORLD_X_INSERTION_FINGER_SEPARATION_WORLD_Y"
        # Do NOT lift based on a successful Gripper FJT alone.
        # Previous CI #43563447828: FJT SUCCEEDED q≈.01067m, yet no
        # native Gazebo contact with either finger and rod did not lift.
        # Capture native WORLD pose of BOTH links, preserving independent
        # evidence of any mismatch with the original URDF/JointState FK.
        native_raw=Path(os.environ["CH07_77_G04B_NATIVE_RAW"])
        assert native_raw.is_file(), "G04B_NATIVE_CONTACT_RECORDER_ABSENT"
        before_close_bytes=native_raw.stat().st_size
        # NEW native physics admission gate based on CI #43571761460:
        # wrist contacted the 18mm support wall at x=.691 z≈1.873 before
        # one finger stopped at q=0. A successful arm Action is NOT enough.
        # Read the passive support collision sensor generated only in G04B.
        support_raw=Path(os.environ["CH07_77_G04B_SUPPORT_RAW"])
        assert support_raw.is_file() and support_raw.stat().st_size>0,(
            "G04B_NATIVE_SUPPORT_CONTACT_OBSERVER_MISSING_NO_CLOSE")
        wrist_support_hits=support_raw.read_bytes().count(
            b"my_robot::link_wrist::link_wrist_collision")
        report["wrist_support_contact_mentions_preclose"]=wrist_support_hits
        if wrist_support_hits:
            raise RuntimeError(
                "G04B_WRIST_SUPPORT_PHYSICAL_INTERFERENCE_NO_GRIPPER_GOAL "+
                str(wrist_support_hits))
        report["native_before_close"]={
            link:native_robot_link_pose(link)
            for link in ("link_wrist","finger1","finger2")}
        n1=report["native_before_close"]["finger1"]["world_xyz_m"]
        n2=report["native_before_close"]["finger2"]["world_xyz_m"]
        real_sep={"dx":abs(n2[0]-n1[0]),"dy":abs(n2[1]-n1[1]),
                  "dz":abs(n2[2]-n1[2])}
        report["native_open_finger_separation_world_m"]=real_sep
        assert real_sep["dy"]>=.054 and real_sep["dx"]<=.010 and real_sep["dz"]<=.010,(
            "G04B_REAL_OPPOSING_FINGERS_NOT_ALIGNED_WORLD_Y_NO_CLOSE")
        # A Gazebo link origin is NOT its collision box centre.
        # Original finger collision extends local z=[0,.08] from each
        # link origin. Native links at z≈1.894m are correct: their rotated
        # collision volumes run upward to z≈1.954m and overlap the actual
        # rod span [1.90,1.98] by ~54mm. The prior centre-only guard
        # incorrectly rejected genuine overlap before a finger Goal.
        rod_z_low=report["pose_snapshots"]["approach"][2]-meta["height_m"]/2
        rod_z_high=report["pose_snapshots"]["approach"][2]+meta["height_m"]/2
        collision_z_overlaps={}
        for link in ("finger1","finger2"):
            info=report["native_before_close"][link]
            link_z=info["world_xyz_m"][2]
            roll,pitch,yaw=info["world_rpy_rad"]
            upward_world_z=math.cos(roll)*math.cos(pitch)
            end_z=link_z+.08*upward_world_z
            zlo,zhi=sorted((link_z,end_z))
            overlap=max(0.0,min(zhi,rod_z_high)-max(zlo,rod_z_low))
            collision_z_overlaps[link]=overlap
        report["native_finger_collision_box_vertical_overlap_m"]=collision_z_overlaps
        assert min(collision_z_overlaps.values())>=.020,(
            "G04B_REAL_FINGER_COLLISION_VOLUME_DOES_NOT_REACH_ROD_NO_CLOSE")
        # New physical evidence CI #43585645201: the previously staged
        # finger1=12mm goal pushed the real rod 4.48mm toward finger2;
        # finger2 collided at q≈0, FJT correctly ABORTED(-5).
        # Original collision faces open 45mm; physical cylinder Ø24mm;
        # nominal two-sided first contact q=(.045-.024)/2=.0105m.
        # Symmetric q=.011m adds 0.5mm per-side contact compression.
        # Do not move the rod, change controller tolerances, fake attach,
        # teleport, or claim success without native bilateral forces.
        # Raw synchronized native scene/contact CI #43684696292:
        # physical cylinder left first finger's collision box by ~60.323s
        # while both finger FJT values stayed ~10.5mm and the 24mm rod
        # exactly matched the 45mm opening minus 2*10.5mm. Existing
        # contract allows <=1.0mm PER finger compression; use that maximum
        # (goal 11.5mm) to test true contact normal force margin, no robot
        # friction/effort/tolerance changes, no fake attachment.
        compression=.001
        physical_q=symmetric_close_joint_target(
            meta["physical_open_face_gap_m"],2*meta["radius_m"],
            compression_per_finger_m=compression)
        report["physical_symmetric_close_compression_per_finger_m"]=compression
        report["physical_symmetric_close_target_per_joint_m"]=physical_q
        report["physical_close_strategy"]="ONE_SIMULTANEOUS_BILATERAL_FJT"
        report["finger_results"].append(
            w.grip_goal("contact_close",physical_q,physical_q))
        report["finger_goal_count"]+=1
        w.spin_for(.65)
        report["pose_snapshots"]["closed"]=rod_pose()
        report["actual_finger_joints_after_close"]=w.joints[-1]["fingers"]
        report["rod_displacement_after_close_m"]=math.dist(
            report["pose_snapshots"]["closed"],report["pose_snapshots"]["initial"])
        report["native_after_close"]={
            link:native_robot_link_pose(link)
            for link in ("link_wrist","finger1","finger2")}
        with native_raw.open("rb") as src:
            src.seek(before_close_bytes)
            new_contact_bytes=src.read(40_000_000)
        report["new_native_contact_bytes_after_close"]=len(new_contact_bytes)
        report["native_per_finger_contact_mentions_after_close"]={
            finger:new_contact_bytes.count((
                "my_robot::"+finger+"::"+finger+"_collision").encode())
            for finger in ("finger1","finger2")}
        if not all(n>=3 for n in report[
                "native_per_finger_contact_mentions_after_close"].values()):
            raise RuntimeError(
                "G04B_NO_NATIVE_BILATERAL_FINGER_CONTACT_BEFORE_LIFT")
        # Final after-run audit still requires positive actual contact force
        # and dynamic world pose lift+hold+release; this is merely a gate.

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
        # Original physical CI #43597860243: gripping, lift 13.032cm,
        # 1.3s stable hold PASS; old transfer [.477,.217,1.759] moved
        # real rod to (.643,.088,1.839), outside bin, with 75 native
        # wrist↔rod collisions at sim 64.873-64.964. Do NOT open there.
        # Transport actual dynamic rod into BIN_XY while HIGH above it,
        # then lower without lateral sweep and only release if the
        # independent rod world pose and gripper custody both pass.
        # Cycle07 real Gazebo contact sim 66.427: link4 struck bin support.
        # Plan around the exact unchanged obstacle instead of retrying a
        # blocked velocity/position goal with relaxed tolerances.
        report["cycle08_native_bin_in_moveit_scene"]=w.register_real_bin_planning_collision(
            os.environ["CH07_181_C08_GAZEBO_WORLD_SDF"])
        held_world=report["pose_snapshots"]["held"]
        held_fk=measured_finger_center(w.joints[-1]["arm"])
        held_offset=custody_offset(held_world,held_fk)
        report["physical_held_rod_offset_from_finger_center"]=held_offset
        # Original #43604397028: nominal frozen lift-wrist subtraction
        # produced a HIGH goal that missed actual cylinder XY by 0.150m,
        # and true 5DOF geometric custody by 0.213m.
        # Compute initial high goal from actual measured original arm
        # JointState and original 100mm wrist-to-finger FK instead.
        high_target=exact_fk_high_bin_wrist_target(
            dict(w.joints[-1]["arm"]),held_world)
        report["transport_high_wrist_goal"]=high_target
        # Raw #43605465669: coarse MoveGroup joint constraint .035rad
        # allowed up to .03358rad actual joint error, leaving 51mm physical
        # bin miss. Its SECOND lateral correction pushed actual held rod
        # AWAY from bin, with true custody drift rising 25.7->70.2mm.
        # Reuse the existing .002rad precise target contract already
        # used for G04B final x-alignment, rather than a second motion.
        # The original 24mm rod slipped by 16.83cm in #43683249305
        # DESPITE precise 1.5mrad arm tracking: yaw from 0.018 to 0.421
        # rotated the jaw separation direction ~0.37rad because q4
        # stayed pi/2. Counter-rotate q4 to keep actual WORLD jaw normal
        # as close as reachable to the measured physical held orientation.
        # At q_wrist=0, changing q4 does NOT move the target finger-centre
        # XYZ or the cylinder's ideal transport goal.
        held_arm_actual=dict(w.joints[-1]["arm"])
        # Cycle14: exact held-time input provenance for the adaptive selector.
        # Read-only; never substitute earlier lift final JointState.
        report["cycle14_actual_held_arm_jointstate_pre_high"]=held_arm_actual
        nominal_high_arm=arm_ik_tilted_fingers(*high_target)
        jaw_plan=high_carry_jaw_compensation(
            held_arm_actual,nominal_high_arm)
        high_joint_target=jaw_plan["target"]
        if os.environ.get("CH07_181_C12_BIN_YAW_ONLY")=="YES":
            # Actual solid bin same size, centre and top; yaw-only test fixture.
            # 5mm source goal and native FCL/Gazebo all mandatory.
            c12=source_bin_rotated_high_goal(
                held_arm_actual,held_world,
                report["cycle08_native_bin_in_moveit_scene"])
            high_joint_target=c12["joint_goal"]
            report["cycle12_rotated_real_bin_high_goal"]=c12
            report["cycle12_collision_checked_plan_only"]=w.arm_goal(
                "cycle12_bin_yaw_high_plan_only",high_target,
                plan_only=True,joint_override=high_joint_target)
        elif os.environ.get("CH07_181_C10_CLEARANCE_HIGH_GOAL")=="YES":
            # Offline original OBB SAT is ONLY a candidate; actual FCL
            # plan_only must pass before any real high motion.
            candidate=source_bin_clearance_high_goal(
                held_arm_actual,held_world,
                report["cycle08_native_bin_in_moveit_scene"])
            high_joint_target=candidate["joint_goal"]
            report["cycle10_original_bin_high_candidate"]=candidate
            report["cycle10_collision_checked_plan_only"]=w.arm_goal(
                "cycle10_original_bin_high_plan_only",high_target,
                plan_only=True,joint_override=high_joint_target)
        elif os.environ.get("CH07_181_C09_NEGATIVE_ELBOW_TRIAL")=="YES":
            # Cycle08: exact high goal collides with real static bin link4.
            # ONE alternative: other IK elbow branch; stop if OMPL cannot
            # find a collision-free plan BEFORE sending any real high motion.
            alt=alternative_high_elbow_target(
                held_arm_actual,held_world,high_target)
            high_joint_target=alt["joint_goal"]
            report["cycle09_elbow_alternative_geometry"]=alt
            report["cycle09_collision_checked_plan_only"]=w.arm_goal(
                "cycle09_high_elbow_alternative_plan_only",high_target,
                plan_only=True,joint_override=high_joint_target)

        report["transport_high_jaw_axis_plan"]=jaw_plan
        report["transport_high_exact_5dof_joint_target"]=high_joint_target
        report["transport_high_movegroup_joint_constraint_rad"]=.002
        report["arm_results"].append(
            w.arm_goal("transfer_high_above_bin",high_target,
                       joint_override=high_joint_target))
        report["arm_goal_count"]+=1
        w.spin_for(.5)
        report["transport_high_measured_jaw_axis_change_rad"]=real_jaw_world_axis_change(
            held_arm_actual,dict(w.joints[-1]["arm"]))
        report["transport_high_measured_jaw_axis_world"]=real_jaw_world_axis(
            dict(w.joints[-1]["arm"]))
        if report["transport_high_measured_jaw_axis_change_rad"]>MAX_ACTUAL_JAW_NORMAL_DRIFT_RAD:
            raise RuntimeError("G04B_181_REAL_JAW_WORLD_DIRECTION_LOST_DURING_CARRY")
        report["transport_high_jointstate_target_audit"]=assess_precise_high_arrival(
            high_joint_target,dict(w.joints[-1]["arm"]),held_offset)
        if not report["transport_high_jointstate_target_audit"][
                "real_arm_tracking_scoped_pass"]:
            audit=report["transport_high_jointstate_target_audit"]
            if (audit["max_joint_error_rad"]<=.01 and
                    audit["ideal_object_bin_xy_error_m"]>.005):
                raise RuntimeError("G04B_181_HIGH_SOURCE_FK_GOAL_GEOMETRY_OVER_5MM")
            raise RuntimeError("G04B_181_HIGH_MOVEGROUP_ACTUAL_JOINT_TRACKING_FAILED")
        above=rod_pose()
        report["pose_snapshots"]["transfer_high"]=above
        high_fk=measured_finger_center(w.joints[-1]["arm"])
        report["transport_high_custody_drift_m"]=custody_drift(
            above,high_fk,held_offset)
        report["transport_high_bin_xy_error_m"]=math.hypot(
            above[0]-.55,above[1]-.25)
        if not high_arrival_valid(above,report["transport_high_custody_drift_m"]):
            raise RuntimeError("G04B_181_REAL_ROD_NOT_ABOVE_BIN_WITH_SECURE_GRASP")
        # No second high XY MoveGroup Goal. G04B #43605465669 proved
        # its predicted overshoot (~53mm) and measured dynamic rod slip.
        # Preserve distinct receipts; do NOT fabricate a second test.
        report["transport_second_lateral_goal"]="NOT_RUN_UNSTABLE_RAW_43605465669"
        report["pose_snapshots"]["transfer_high_precise"]=list(above)
        report["transport_high_precise_custody_drift_m"]=report[
            "transport_high_custody_drift_m"]
        report["transport_high_precise_bin_xy_error_m"]=report[
            "transport_high_bin_xy_error_m"]
        if not precise_high_arrival_valid(
                above,report["transport_high_precise_custody_drift_m"]):
            raise RuntimeError("G04B_181_REAL_ROD_NOT_PRECISELY_CENTERED_HIGH")
        high_refined=high_target
        # CI #43599620070: high transfer had only 4.85mm grasp custody
        # drift, but uncorrected lower step changed world finger pitch
        # ~0.31rad, leading to 108mm real rod slip despite both contacts.
        # Use original wrist joint to preserve measured WORLD finger tilt,
        # not fake attachment or altered friction/force.
        high_arm_actual=dict(w.joints[-1]["arm"])
        lower=[high_refined[0],high_refined[1],LOWER_WRIST_Z]
        lower_nominal=arm_ik_tilted_fingers(*lower)
        # Preserve previous lower wrist command as a CONTROLLED candidate.
        # It does NOT preserve true physical tool orientation at q4=pi/2;
        # exact 5DOF tool axis is recorded independently below.
        if os.environ.get("CH07_181_C16_COLLISION_SAFE_LOWER")=="YES":
            # Cycle15's original lower goal intersects REAL solid bin/link4.
            # Source OBB preview is necessary but not MoveIt FCL proof.
            lower_plan=collision_safe_lower_target(
                high_arm_actual,held_offset,
                report["cycle08_native_bin_in_moveit_scene"])
            lower_oriented=lower_plan["target"]
            report["cycle16_source_solid_bin_lower_candidate"]=lower_plan
            report["cycle16_lower_fcl_plan_only"]=w.arm_goal(
                "cycle16_lower_original_bin_plan_only",lower,
                joint_override=lower_oriented,plan_only=True)
            report["lower_exact_world_jaw_plan"]="CYCLE16_SOLID_BIN_SAFE_LOWER"
        elif os.environ.get("G04B_CYCLE06_REACHABLE_RELEASE")=="YES":
            # One new waypoint, no FJT/tolerance/gain change: avoid the
            # independently observed native q3 stall at ~1.132 rad.
            lower_plan=reachable_release_waypoint(
                high_arm_actual,lower_nominal,held_offset)
            lower_oriented=lower_plan["target"]
            report["lower_reachable_release_plan"]=lower_plan
            report["lower_exact_world_jaw_plan"]="CYCLE06_REACHABLE_SHORT_DROP"
        elif os.environ.get("G04B_CYCLE05_PGS_JAW_GOAL")=="YES":
            lower_plan=exact_world_jaw_lower_plan(
                high_arm_actual,lower_nominal,held_offset)
            lower_oriented=lower_plan["target"]
            report["lower_exact_world_jaw_plan"]=lower_plan
        else:
            lower_oriented=historical_wrist_bias_lower_goal(
                high_arm_actual,lower_nominal)
            report["lower_exact_world_jaw_plan"]="NOT_RUN_DEFAULT"
        report["transport_high_measured_finger_tilt_rad"]=finger_tilt(high_arm_actual)
        report["transport_lower_wrist_goal"]=lower
        report["transport_lower_joint_target_with_pitch_compensation"]=lower_oriented
        lower_movegroup=w.arm_goal(
            "lower_into_bin",lower,joint_override=lower_oriented,
            defer_lower_fjt_recovery=True)
        report["arm_results"].append(lower_movegroup)
        report["arm_goal_count"]+=1
        if os.environ.get("G04B_CYCLE06_REACHABLE_RELEASE")=="YES":
            # Fail closed: MoveGroup SUCCEEDED does NOT prove real q.
            # Do not re-send the same blocked q3 Goal via FJT.
            w.spin_for(.3)
            actual=dict(w.joints[-1]["arm"])
            errors={name:abs(actual[name]-lower_oriented[name]) for name in ARM}
            report["lower_reachable_release_actual_joint_errors_rad"]=errors
            report["lower_reachable_release_actual_jointstate"]=actual
            if (lower_movegroup.get("strict_joint_feedback_deferred_to_fjt")
                    or max(errors.values())>JOINT_GOAL_TOL_RAD):
                raise RuntimeError("G04B_CYCLE06_ACTUAL_LOWER_JOINT_TRACKING_FAILED")
        if lower_movegroup.get("strict_joint_feedback_deferred_to_fjt"):
            # Native dynamic object remains above the bin while the arm
            # joint3 trails the MoveGroup goal. Do not issue another motion
            # if the object is outside the ORIGINAL 9cm bin XY envelope.
            lower_mid_rod=rod_pose()
            report["lower_midway_native_dynamic_rod_pose"]=lower_mid_rod
            lower_mid_xy=math.hypot(lower_mid_rod[0]-.55,
                                    lower_mid_rod[1]-.25)
            report["lower_midway_bin_xy_error_m"]=lower_mid_xy
            if lower_mid_xy>.09:
                raise RuntimeError("G04B_181_LOWER_FJT_OBJECT_OUTSIDE_BIN_XY_STOP")
            strict_settle=w.arm_precision_settle(lower_oriented)
            report["lower_into_bin_direct_fjt_settle"]=strict_settle
            report["arm_results"].append(strict_settle)
        report["lower_into_bin_feedback_resolved"]=True
        w.spin_for(.5)
        report["transport_legacy_scalar_tilt_drift_rad"]=actual_finger_tilt_drift(
            high_arm_actual,w.joints[-1]["arm"])
        report["transport_actual_tool_world_axis_change_rad"]=actual_tool_axis_angle_rad(
            high_arm_actual,w.joints[-1]["arm"])
        report["transport_actual_tool_world_axis_high"]=original_finger_tool_z_axis(
            high_arm_actual)
        report["transport_actual_tool_world_axis_lower"]=original_finger_tool_z_axis(
            w.joints[-1]["arm"])
        # q4≈pi/2 means qwrist is rotated into a different axis.
        # DO NOT claim preserved tool orientation using theta+qwrist;
        # native real rod/finger contacts + world pose provide custody.
        report["pose_snapshots"]["pre_release"]=rod_pose()
        release_pose=report["pose_snapshots"]["pre_release"]
        lower_fk=measured_finger_center(w.joints[-1]["arm"])
        report["pre_release_custody_drift_m"]=custody_drift(
            release_pose,lower_fk,held_offset)
        report["pre_release_bin_xy_error_m"]=math.hypot(
            release_pose[0]-.55,release_pose[1]-.25)
        report["pre_release_gripper_actual_jointstate"]=dict(
            w.joints[-1]["fingers"])
        if not all(abs(v-.011)<=.003 for v in
                   report["pre_release_gripper_actual_jointstate"].values()):
            raise RuntimeError("G04B_181_ACTUAL_GRIPPER_OPENED_DURING_CARRY")
        sim_now=w.get_clock().now().nanoseconds*1e-9
        report["pre_release_sim_stamp"]=sim_now
        native_dir=Path(os.environ["CH07_77_G04B_NATIVE_RAW"]).parent
        cli_contact_diagnostic=require_bilateral_pre_release_contact(
            native_dir,sim_now)
        if os.environ.get("CH07_181_C17_NATIVE_ECS_FORCE")=="YES":
            # Actual read-only same-ECS-frame contact + native force.
            # The large asynchronous gz topic text log remains unmodified
            # and is independently audited AFTER release in the original
            # physical acceptance script; do not infer force from old data.
            ecs_contact=require_bilateral_same_ecs_frame_force(
                native_dir/"gazebo_rod_finger_contact_same_ecs_frame.csv",sim_now)
            report["cycle17_async_cli_contact_diagnostic"]=cli_contact_diagnostic
            report["cycle17_same_ecs_native_force"]=ecs_contact
            report["pre_release_recent_native_contact"]=(
                ecs_contact if ecs_contact["both_native_fresh_positive_force"]
                else cli_contact_diagnostic)
        else:
            report["pre_release_recent_native_contact"]=cli_contact_diagnostic
        # Original scalar FK receipt was invalid after nonzero q_wrist.
        # Independent contemporaneous real Gazebo collision and force
        # are stronger custody proof. Object XY/Z, closed JointState
        # and later physically settled ROI/height remain mandatory.
        if not pre_release_valid(
                release_pose,report["pre_release_custody_drift_m"],
                report["pre_release_recent_native_contact"]):
            raise RuntimeError("G04B_181_REAL_ROD_OUTSIDE_SAFE_BIN_RELEASE_ENVELOPE_OR_LOST_NATIVE_GRIP")
        if os.environ.get("CH07_181_C18_RELEASE_RETRACT")=="YES":
            # The original wrist OBB intersects the actual falling rod.
            # ONE new concurrent FJT wrist retreat, source/FCL preflight
            # required. Never assume the rod remains fixed during motion.
            actual_lower=dict(w.joints[-1]["arm"])
            retreat=source_release_wrist_retract(
                actual_lower,release_pose,
                report["cycle08_native_bin_in_moveit_scene"])
            report["cycle18_source_release_retract"]=retreat
            report["cycle18_official_moveit_plan_only"]=w.arm_goal(
                "cycle18_release_retract_plan_only",None,
                plan_only=True,joint_override=retreat["target"])
            fingers,arm=w.release_and_retract_fjt(retreat["target"])
            report["finger_results"].append(fingers)
            report["finger_goal_count"]+=1
            report["arm_results"].append(arm)
            report["arm_goal_count"]+=1
            report["cycle18_rod_world_after_retract"]=rod_pose()
        else:
            report["finger_results"].append(w.grip_goal("release",0.0))
            report["finger_goal_count"]+=1
        w.spin_for(2.0)
        report["pose_snapshots"]["settled"]=rod_pose()
        obj=report["pose_snapshots"]["settled"]
        report["placement_xy_error_m"]=math.hypot(obj[0]-.55,obj[1]-.25)
        # G04B's new 80mm rod settles on destination bin top z=1.73;
        # the centre must settle at 1.73+0.08/2=1.77m. Same ±55mm
        # allowed error as before; do not claim an 80mm rod is 240mm.
        expected_settled_center_z=1.73+meta["height_m"]/2
        report["placement_center_expected_z_m"]=expected_settled_center_z
        report["placement_center_height_error_m"]=abs(obj[2]-expected_settled_center_z)
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
        # Preserve exact joint and native rod pose on every unsuccessful
        # contact-close attempt. FJT status SUCCESS is not a physics PASS.
        if w.last_grip_data is not None:
            report["last_gripper_result_even_on_failure"]=w.last_grip_data
            if w.last_grip_data["name"]=="free_space_close":
                report["free_space_actual_finger_joints_on_failure"] = w.joints[-1]["fingers"]
            if w.last_grip_data["name"]=="contact_close":
                try:
                    report["pose_snapshots"]["closed_after_failure"]=rod_pose()
                    report["rod_shift_after_close_even_on_failure_m"]=math.dist(
                        report["pose_snapshots"]["closed_after_failure"],
                        report["pose_snapshots"].get("initial",[0,0,0]))
                    report["native_after_failure"]={
                        link:native_robot_link_pose(link)
                        for link in ("finger1","finger2")}
                except Exception as snapshot_error:
                    report["failure_snapshot_error"]=repr(snapshot_error)
        # Read-only FJT evidence survives a real action ABORTED exception.
        if w.last_arm_settle_data is not None:
            report["last_arm_settle_even_on_failure"]=w.last_arm_settle_data
        if w.last_high_joint2_causal is not None:
            report["last_high_joint2_causal_even_on_failure"]=w.last_high_joint2_causal
        if w.last_lower_joint3_causal is not None:
            report["last_lower_joint3_causal_even_on_failure"]=w.last_lower_joint3_causal
        report["joint_state_samples"]=len(w.joints)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        w.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=="__main__":
    main()
