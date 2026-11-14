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
from control_msgs.msg import JointTrajectoryControllerState, JointTolerance
from ch07_181_arm_settle_contract import assess_arm_settle, JOINT_GOAL_TOL_RAD
from ch07_181_symmetric_grasp_contract import symmetric_close_joint_target
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
    """Original URDF wrist-to-finger collision centre FK, local z=.10m.

    Applicable when actual joint4≈pi/2 and joint_wrist≈0, checked before
    close against native Gazebo true link poses.
    """
    r=.5*math.sin(arm["joint2"])+math.sin(arm["joint2"]+arm["joint3"])
    yaw=arm["joint1"]
    tilt=arm["joint2"]+arm["joint3"]+arm["joint_wrist"]
    # Each finger starts at wrist local z=.06; box centre adds +.04.
    # Thus the real collision-zone centre is at local z=.10.
    return [
        (r+.10*math.sin(tilt))*math.cos(yaw),
        (r+.10*math.sin(tilt))*math.sin(yaw),
        .6+.5*math.cos(arm["joint2"])+math.cos(arm["joint2"]+arm["joint3"])
          +.10*math.cos(tilt)
    ]


class Witness(Node):
    def __init__(self):
        super().__init__("ch07_77_g04b_actual_gazebo_contact_witness")
        self.move=ActionClient(self,MoveGroup,"/move_action")
        self.arm_direct=ActionClient(self,FollowJointTrajectory,
                                     "/arm_group_controller/follow_joint_trajectory")
        self.grip=ActionClient(self,FollowJointTrajectory,
                               "/gripper_group_controller/follow_joint_trajectory")
        self.joints=[]
        self.last_grip_data=None
        self.controller_samples=[]
        self.create_subscription(JointTrajectoryControllerState,
            "/gripper_group_controller/controller_state",
            self.on_controller_state,10)
        self.create_subscription(JointState,"/joint_states",self.on_state,10)

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
        self.controller_samples=self.controller_samples[-100:]

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

    def arm_goal(self,label,xyz,plan_only=False,joint_override=None):
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
        row={"name":"post_movegroup_direct_fjt_arm_settle",
             "desired":target,"actual":observed,"error_rad":errors,
             "action_status":int(outcome.status),
             "result_error":int(outcome.result.error_code),
             "goal_tolerance_rad":JOINT_GOAL_TOL_RAD,
             "goal_time_tolerance_s":2,"verdict":verdict}
        if verdict!="ARM_SETTLE_SCOPED_PASS":
            raise RuntimeError("G04B_181_ARM_SETTLE_FAILED_"+str(row))
        return row

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
        nominal_pregrasp=arm_ik_tilted_fingers(*pregrasp)
        report["arm_results"].append(
            w.arm_goal("pregrasp",pregrasp,joint_override=nominal_pregrasp))
        report["arm_goal_count"]+=1
        # CI #43584052832: MoveGroup-only led to frozen finger with reference
        # 12mm; one DIRECT arm FJT settle restored actual bilateral control.
        # Preserve original MoveGroup planned+executed motion and independent
        # contact/lift/hold/place witness; no force/attach/teleport.
        report["post_movegroup_arm_settle"]=w.arm_precision_settle(nominal_pregrasp)
        report["arm_goal_count"]+=1
        report["pose_snapshots"]["pregrasp"]=rod_pose()
        assert math.dist(report["pose_snapshots"]["pregrasp"],
                         report["pose_snapshots"]["initial"])<=.008,(
            "G04B_ROD_DISTURBED_BEFORE_APPROACH")
        # NEW smallest failing-boundary test. Before approaching the
        # support/rod, with both finger tips safely behind the object,
        # drive two original GazeboSimSystem prismatic joints once.
        # It discriminates controller/rotated-URDF dynamic failure
        # from collision only after actual grasp insertion. The §7.6
        # accepted empty-world test is NOT rerun.
        preflight_tip=measured_finger_center(w.joints[-1]["arm"])
        assert preflight_tip[0]<=.62,(
            "G04B_CLEARANCE_FINGER_PREFLIGHT_TOO_CLOSE_TO_ROD")
        # New bounded A/B diagnosis for the *failed* q4=pi/2 mode.
        # Earlier CI #43572765627 with one simultaneous two-finger Goal
        # had finger1=11.405mm, finger2≈0 in EMPTY clearance, no contact.
        # Test each original prismatic interface independently with both
        # names in each FJT Goal, then compare staggered operation. This
        # is not a repeat of the accepted §7.6 straight-arm demo.
        report["finger_clearance_preflight"]=[]
        report["finger_clearance_preflight_target_m"]=.012
        report["finger_clearance_preflight_phase"]="BEFORE_ROD_OR_SUPPORT_APPROACH"
        isolated_cases=(
            ("isolated_finger1",.012,0.0),
            ("isolated_reopen_1",0.0,0.0),
            ("isolated_finger2",0.0,.012),
            ("isolated_reopen_2",0.0,0.0),
            ("stagger_finger1_first",.012,0.0),
            ("stagger_finger2_second",.012,.012),
            ("stagger_reopen",0.0,0.0),
        )
        for name,q1,q2 in isolated_cases:
            rec=w.grip_goal(name,q1,q2,diagnostic=True)
            report["finger_clearance_preflight"].append(rec)
            if math.dist(rod_pose(),report["pose_snapshots"]["initial"])>.008:
                raise RuntimeError("G04B_OBJECT_MOVED_DURING_FREE_SPACE_DIAG")
        report["free_space_joint_state_after_close"]=w.joints[-1]["fingers"]
        report["free_space_diagnostics_all_tracking_pass"]=all(
            x["joint_tracking_pass"] for x in report["finger_clearance_preflight"])
        report["controller_state_traces_last_10"]=w.controller_samples[-10:]
        if not report["free_space_diagnostics_all_tracking_pass"]:
            raise RuntimeError(
                "G04B_ISOLATED_VS_STAGGERED_JOINT_ACTUATION_UNDER_ROTATED_ARM_FAIL_NO_APPROACH")
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
        physical_q=symmetric_close_joint_target(
            meta["original_open_finger_gap_m"],2*meta["radius_m"])
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
        report["arm_results"].append(w.arm_goal("transfer",[.477,.217,1.759]))
        report["arm_goal_count"]+=1
        report["pose_snapshots"]["pre_release"]=rod_pose()
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
        report["joint_state_samples"]=len(w.joints)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        w.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=="__main__":
    main()
