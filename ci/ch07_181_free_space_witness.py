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
from ch07_181_free_space_contract import (
 FINGERS,TOLERANCE_M,controller_sample,accept_real_finger_state)

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
       arm=mon.send(mon.arm,ARM,ARM_TARGET,5,.05,"q4_pregrasp_setup")
       report["arm_setup"]=arm
       report["arm_setup_goal_count"]=1
       a=mon.joint_samples[-1]["arm"]
       report["arm_actual"]=a
       if arm["action_status"]!=GoalStatus.STATUS_SUCCEEDED or arm["result_error_code"]!=0:
          raise RuntimeError("G04B_181_ARM_SETUP_ACTION_FAILED")
       if abs(a["joint4"]-math.pi/2)>.025:
          raise RuntimeError("G04B_181_Q4_PREGRASP_NOT_REACHED")
       if max(abs(a[n]-ARM_TARGET[i]) for i,n in enumerate(ARM))>.075:
          raise RuntimeError("G04B_181_ARM_SETUP_NOT_TRACKED")
       report["gz_before_finger"]=gz_snapshot("before_finger")
       before_ctl=len(mon.controller_samples)
       report["finger_goal_count"]=1
       finger=mon.send(mon.grip,FINGERS,(.012,.012),2,TOLERANCE_M,
                       "bilateral_free_space_12mm")
       report["finger_result"]=finger
       report["gz_after_finger"]=gz_snapshot("after_finger")
       measured=mon.joint_samples[-1]["fingers"]
       report["independent_joint_state_after"]=mon.joint_samples[-1]
       relevant=[row for row in mon.controller_samples[before_ctl:]
                    if row["stamp"]>=finger["before_stamp"]]
       report["controller_state_during_goal"]=relevant
       report["controller_state_schema_errors"]=mon.controller_errors
       report["joint_state_during_goal"]=[
          row for row in mon.joint_samples if row["stamp"]>=finger["before_stamp"]]
       verdict=accept_real_finger_state(
          finger["action_status"],finger["result_error_code"],measured,
          FINGER_TARGET,relevant,finger["after_stamp"],finger["before_stamp"])
       if mon.controller_errors:verdict="JTC_SCHEMA_INVALID"
       report["verdict"]=verdict
       if verdict!="FREE_SPACE_ACTUATION_SCOPED_PASS":
          raise RuntimeError("G04B_181_"+verdict)
       report["status"]="SCOPED_PASS_FREE_SPACE_ONLY"
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
