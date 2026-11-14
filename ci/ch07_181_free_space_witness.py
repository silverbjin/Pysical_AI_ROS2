#!/usr/bin/env python3
"""Issue #181. ONE cold-start real GazeboSimSystem free-space experiment.

No object, pedestal, grasp, MoveIt, fake hardware, or re-run of G00..G04A.
A single arm FJT sets the *previously observed* q4~pi/2 pregrasp posture;
a single subsequent two-finger FJT goal tests real control.
"""
import json,math,os,subprocess,time,traceback
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTolerance,JointTrajectoryControllerState
from trajectory_msgs.msg import JointTrajectoryPoint
from sensor_msgs.msg import JointState
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints,JointConstraint,MoveItErrorCodes
from ch07_181_free_space_contract import (
 FINGERS,ISOLATED_SEQUENCE,TOLERANCE_M,MOVEGROUP_PREGRASP_JOINT_TOL_RAD,validate_arm_mode,arm_result_accepted,validate_preopen_mode,controller_sample,accept_real_finger_state)

ARM=("joint1","joint2","joint3","joint4","joint_wrist")
# Exact prior G04B pregrasp arm goal from independently audited #43574030542.
ARM_TARGET=(0.,-0.29612883318787947,0.9853157274797393,
            1.5707963267948966,0.)
FINGER_TARGET={n:.012 for n in FINGERS}

def gz_snapshot(label):
    result={}
    for link in ("link_wrist","finger1","finger2"):
        cmd=["gz","model","--model","my_robot","--link",link,"--pose"]
        try:
            run=subprocess.run(cmd,text=True,capture_output=True,timeout=10)
            result[link]={"returncode":run.returncode,"stdout":run.stdout[-4000:],
                          "stderr":run.stderr[-1000:]}
        except Exception as exc:
            result[link]={"error":repr(exc)}
    return {"label":label,"links":result}

class Monitor(Node):
 def __init__(self):
    super().__init__("ch07_181_one_cold_start_free_space_witness")
    self.arm=ActionClient(self,FollowJointTrajectory,
                          "/arm_group_controller/follow_joint_trajectory")
    self.move=ActionClient(self,MoveGroup,"/move_action")
    self.grip=ActionClient(self,FollowJointTrajectory,
                           "/gripper_group_controller/follow_joint_trajectory")
    self.joint_samples=[]
    self.controller_samples=[]
    self.controller_errors=[]
    self.create_subscription(JointState,"/joint_states",self.on_joint,10)
    self.create_subscription(JointTrajectoryControllerState,
      "/gripper_group_controller/controller_state",self.on_controller,10)
 def on_joint(self,msg):
    d=dict(zip(msg.name,msg.position))
    if all(n in d and math.isfinite(d[n]) for n in ARM+FINGERS):
       stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
       self.joint_samples.append({"stamp":stamp,
          "arm":{n:float(d[n]) for n in ARM},
          "fingers":{n:float(d[n]) for n in FINGERS}})
       self.joint_samples=self.joint_samples[-3000:]
 def on_controller(self,msg):
    try:
       self.controller_samples.append(controller_sample(msg))
       self.controller_samples=self.controller_samples[-3000:]
    except Exception as exc:
       self.controller_errors.append(repr(exc))
 def spin_for(self,seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
       rclpy.spin_once(self,timeout_sec=.08)
 def await_future(self,future,seconds,label,cancel=None):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
       rclpy.spin_once(self,timeout_sec=.08)
       if future.done():return future.result()
    if cancel:
       try:cancel();self.spin_for(1)
       except Exception:pass
    raise TimeoutError("G04B_181_"+label+"_TIMEOUT")
 def wait_ready(self):
    end=time.monotonic()+45
    while time.monotonic()<end:
       rclpy.spin_once(self,timeout_sec=.1)
       if len(self.joint_samples)>8 and self.arm.server_is_ready() and self.grip.server_is_ready():
          if self.joint_samples[-1]["stamp"]-self.joint_samples[0]["stamp"]>.3:
             return
    raise RuntimeError("G04B_181_REAL_SIMULATION_CONTROLLER_NOT_READY")
 def send(self,client,names,positions,seconds,tolerance_m,label):
    g=FollowJointTrajectory.Goal()
    g.trajectory.joint_names=list(names)
    point=JointTrajectoryPoint()
    point.positions=[float(x) for x in positions]
    point.time_from_start.sec=seconds
    g.trajectory.points=[point]
    for n in names:
       t=JointTolerance()
       t.name=n
       t.position=tolerance_m
       g.goal_tolerance.append(t)
    g.goal_time_tolerance.sec=2
    sent=self.joint_samples[-1]["stamp"]
    handle=self.await_future(client.send_goal_async(g),12,label+"_accept")
    if not handle or not handle.accepted:
       raise RuntimeError("G04B_181_"+label+"_REJECTED")
    result=self.await_future(handle.get_result_async(),seconds+15,
                             label+"_result",handle.cancel_goal_async)
    self.spin_for(.35)
    return {"label":label,"goal_joints":list(names),"goal_positions_m_or_rad":list(positions),
            "goal_tolerance":tolerance_m,"goal_time_tolerance_s":2,
            "before_stamp":sent,"after_stamp":self.joint_samples[-1]["stamp"],
            "action_status":int(result.status),
            "result_error_code":int(result.result.error_code),
            "result_error_string":result.result.error_string}

def main():
    if os.environ.get("CH07_181_GAZEBO_ONLY")!="YES":
       raise RuntimeError("G04B_181_GAZEBO_ONLY_REQUIRED")
    out=Path(os.environ["CH07_181_RECEIPT"])
    report={"scope":"ISSUE_181_ONE_COLD_START_FREE_SPACE_JAZZY_JTC",
            "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
            "status":"FAIL","G00_to_G04A":"NOT_RERUN",
            "G04B_physics":"NOT_RUN","G05":"NOT_RUN","Ch10":"HOLD",
            "rod_and_support":"ABSENT_BY_GENERATED_WORLD_CONTRACT",
            "finger_goal_count":0,"arm_setup_goal_count":0,
            "fjt_position_goal_tolerance_m":TOLERANCE_M,
            "finger_goal":FINGER_TARGET}
    rclpy.init(args=["--ros-args","-p","use_sim_time:=true"])
    mon=Monitor()
    try:
       mon.wait_ready()
       report["start_state"]=mon.joint_samples[-1]
       report["gz_before_arm"]=gz_snapshot("before_arm")
       preopen=validate_preopen_mode(os.environ.get("CH07_181_PREOPEN","NO"))
       report["extra_preopen_before_arm"]=preopen
       if preopen:
          report["finger_goal_count"]=1
          pre_start=len(mon.controller_samples)
          pre=mon.send(mon.grip,FINGERS,(0.,0.),2,TOLERANCE_M,
                       "one_zero_open_before_arm")
          actual=mon.joint_samples[-1]["fingers"]
          ctl=[x for x in mon.controller_samples[pre_start:]
               if x["stamp"]>=pre["before_stamp"]]
          pre["independent_measured_fingers"]=actual
          pre["controller_reference_feedback_error_trace"]=ctl
          pre["independent_joint_state_verdict"]=accept_real_finger_state(
             pre["action_status"],pre["result_error_code"],actual,
             dict.fromkeys(FINGERS,0.),ctl,pre["after_stamp"],pre["before_stamp"])
          report["extra_preopen_result"]=pre
          if pre["independent_joint_state_verdict"]!="FREE_SPACE_ACTUATION_SCOPED_PASS":
             raise RuntimeError("G04B_181_PREOPEN_CONTROL_FAILED")
       arm_mode=validate_arm_mode(os.environ.get("CH07_181_ARM_SETUP","DIRECT_FJT"))
       report["arm_setup_mode"]=arm_mode
       if arm_mode=="MOVEGROUP":
          end=time.monotonic()+45
          while not mon.move.server_is_ready() and time.monotonic()<end:
             rclpy.spin_once(mon,timeout_sec=.1)
          if not mon.move.server_is_ready():
             raise RuntimeError("G04B_181_MOVEGROUP_SERVER_NOT_READY")
          goal=MoveGroup.Goal()
          goal.request.group_name="arm_group"
          goal.request.allowed_planning_time=6.
          goal.request.num_planning_attempts=3
          goal.request.max_velocity_scaling_factor=.17
          goal.request.max_acceleration_scaling_factor=.17
          goal.planning_options.plan_only=False
          goal.planning_options.replan=False
          constraints=Constraints()
          for name,value in zip(ARM,ARM_TARGET):
             joint=JointConstraint()
             joint.joint_name=name
             joint.position=float(value)
             joint.tolerance_above=MOVEGROUP_PREGRASP_JOINT_TOL_RAD
             joint.tolerance_below=MOVEGROUP_PREGRASP_JOINT_TOL_RAD
             joint.weight=1.
             constraints.joint_constraints.append(joint)
          goal.request.goal_constraints.append(constraints)
          sent=mon.joint_samples[-1]["stamp"]
          handle=mon.await_future(mon.move.send_goal_async(goal),15,"movegroup_pregrasp_accept")
          if not handle or not handle.accepted:
             raise RuntimeError("G04B_181_MOVEGROUP_PREGRASP_REJECTED")
          outcome=mon.await_future(handle.get_result_async(),100,"movegroup_pregrasp_result",handle.cancel_goal_async)
          mon.spin_for(.4)
          arm={"label":"q4_pregrasp_setup","goal_joints":list(ARM),
               "goal_positions_m_or_rad":list(ARM_TARGET),
               "action_status":int(outcome.status),
               "result_error_code":int(outcome.result.error_code.val),
               "planned_trajectory_points":len(outcome.result.planned_trajectory.joint_trajectory.points),
               "before_stamp":sent,"after_stamp":mon.joint_samples[-1]["stamp"],
               "path":"MOVEGROUP_ACTUAL_GAZEBO_ARM"}
          if arm["action_status"]!=GoalStatus.STATUS_SUCCEEDED or arm["result_error_code"]!=MoveItErrorCodes.SUCCESS or arm["planned_trajectory_points"]<=0:
             raise RuntimeError("G04B_181_MOVEGROUP_PREGRASP_FAILED")
       else:
          arm=mon.send(mon.arm,ARM,ARM_TARGET,5,.05,"q4_pregrasp_setup")
       report["arm_setup"]=arm
       report["arm_setup_goal_count"]=1
       a=mon.joint_samples[-1]["arm"]
       report["arm_actual"]=a
       if not arm_result_accepted(arm_mode,arm["action_status"],arm["result_error_code"],arm.get("planned_trajectory_points")):
          raise RuntimeError("G04B_181_ARM_SETUP_ACTION_FAILED")
       if abs(a["joint4"]-math.pi/2)>.025:
          raise RuntimeError("G04B_181_Q4_PREGRASP_NOT_REACHED")
       if max(abs(a[n]-ARM_TARGET[i]) for i,n in enumerate(ARM))>.075:
          raise RuntimeError("G04B_181_ARM_SETUP_NOT_TRACKED")
       report["gz_before_finger"]=gz_snapshot("before_finger")
       mode=os.environ.get("CH07_181_COMMAND_SEQUENCE","BILATERAL")
       if mode not in ("BILATERAL","ISOLATED"):raise RuntimeError("G04B_181_BAD_MODE")
       report["command_sequence_mode"]=mode
       cases=(ISOLATED_SEQUENCE if mode=="ISOLATED"
              else (("bilateral_free_space_12mm",(.012,.012)),))
       report["per_goal_results"]=[]
       for label,values in cases:
          before_ctl=len(mon.controller_samples)
          report["finger_goal_count"]+=1
          result=mon.send(mon.grip,FINGERS,values,2,TOLERANCE_M,label)
          measured=mon.joint_samples[-1]["fingers"]
          relevant=[row for row in mon.controller_samples[before_ctl:]
                    if row["stamp"]>=result["before_stamp"]]
          goal={n:float(v) for n,v in zip(FINGERS,values)}
          result["measured_fingers"]=measured
          result["jtc_reference_feedback_error_trace"]=relevant
          result["joint_states_during_goal"]=[
             row for row in mon.joint_samples if row["stamp"]>=result["before_stamp"]]
          verdict=accept_real_finger_state(
             result["action_status"],result["result_error_code"],measured,
             goal,relevant,result["after_stamp"],result["before_stamp"])
          if mon.controller_errors:verdict="JTC_SCHEMA_INVALID"
          result["independent_joint_state_verdict"]=verdict
          report["per_goal_results"].append(result)
          if verdict!="FREE_SPACE_ACTUATION_SCOPED_PASS":
             raise RuntimeError("G04B_181_"+label+"_"+verdict)
       report["gz_after_finger"]=gz_snapshot("after_finger")
       report["independent_joint_state_after"]=mon.joint_samples[-1]
       report["controller_state_schema_errors"]=mon.controller_errors
       report["verdict"]=("ISOLATED_SEQUENCE_SCOPED_PASS" if mode=="ISOLATED"
                          else "FREE_SPACE_ACTUATION_SCOPED_PASS")
       report["status"]="SCOPED_PASS_FREE_SPACE_ONLY"
       if mode=="ISOLATED":
          print("CH07_181_FREE_SPACE_ISOLATED_SEQUENCE_SCOPED_PASS_NO_GRASP",flush=True)
       else:
          print("CH07_181_FREE_SPACE_ACTUATION_SCOPED_PASS_NO_PHYSICAL_GRASP",flush=True)
    except Exception as exc:
       report["reason"]=repr(exc)
       report["status"]="FAIL"
       print("CH07_181_FREE_SPACE_FAIL "+repr(exc),flush=True)
       raise
    finally:
       report["all_controller_samples"]=mon.controller_samples[-3000:]
       report["joint_state_sample_count"]=len(mon.joint_samples)
       report["all_controller_schema_errors"]=mon.controller_errors
       out.parent.mkdir(parents=True,exist_ok=True)
       out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
       mon.destroy_node()
       if rclpy.ok():rclpy.shutdown()
if __name__=="__main__":main()
