#!/usr/bin/env python3
"""Issue #181: fail-closed, ROS-independent interpretation of Jazzy JTC traces.

The accepted G04B source was reading obsolete .desired/.actual fields; Jazzy
control_msgs/JointTrajectoryControllerState publishes .reference/.feedback/.error.
This module never infers physical movement from FJT Action success alone.
"""
import math

FINGERS=("joint_finger1","joint_finger2")
ISOLATED_SEQUENCE=(("isolated_finger1",(.012,0.)),("isolated_reopen",(0.,0.)),("isolated_finger2",(0.,.012)))
# Actual independent JointState at the FINAL no-contact grasp approach
# from failed CI #43586568591; NOT an invented pose or the accepted pregrasp.
FINAL_CONTACT_ARM_POSE=(-0.0009909730618859918,-0.06369211846948007,
                        0.7902071898034883,1.5694273344965841,
                        -0.0005144713775007642)
SINGLE_FINGER2_GOAL=("single_finger2_at_actual_contact_pose",(0.0,0.011))


def validate_arm_mode(mode):
    if mode not in ("DIRECT_FJT","MOVEGROUP"):
        raise ValueError("G04B_181_ARM_SETUP_MODE_INVALID")
    return mode

def arm_result_accepted(mode,status,error_code,planned_trajectory_points=None):
    """MoveGroup error_code SUCCESS=1, but FollowJointTrajectory SUCCESS=0."""
    validate_arm_mode(mode)
    if status!=4:return False
    if mode=="MOVEGROUP":
        return error_code==1 and int(planned_trajectory_points or 0)>0
    return error_code==0

# Fixed 2mm bounded actuation candidate, not a tunable gate or physics reset.
# The observed frozen finger2 was at the exact physical lower limit 0m;
# test a positive, controlled, measured displacement BEFORE arm MoveGroup.
LIMIT_RELEASE_TARGET_M=0.002

def validate_limit_release(value):
    if value not in ("NO","0.002"):
        raise ValueError("G04B_181_LOWER_STOP_RELEASE_ONLY_2MM")
    return LIMIT_RELEASE_TARGET_M if value=="0.002" else 0.0

def validate_preopen_mode(mode):
    if mode not in ("YES","NO"):
        raise ValueError("G04B_181_PREOPEN_MODE_INVALID")
    return mode=="YES"
GOAL_M=0.012
TOLERANCE_M=0.001
# Original G04B precision MoveGroup override uses 2 mrad, not coarse 35 mrad.
MOVEGROUP_PREGRASP_JOINT_TOL_RAD=0.002
# One additional DIRECT arm FJT settlement (narrow post-MoveGroup hypothesis).
ARM_SETTLE_FJT_TOL_RAD=0.01

def validate_settle_mode(mode):
    if mode not in ("YES","NO"):
        raise ValueError("G04B_181_ARM_SETTLE_MODE_INVALID")
    return mode=="YES"

def controller_sample(msg):
    names=list(msg.joint_names)
    if names!=list(FINGERS):
        raise ValueError("G04B_181_CONTROLLER_JOINT_ORDER_MISMATCH")
    data={}
    for field in ("reference","feedback","error"):
        group=getattr(msg,field,None)
        positions=list(getattr(group,"positions",[]))
        if len(positions)!=2 or not all(math.isfinite(float(x)) for x in positions):
            raise ValueError("G04B_181_CONTROLLER_"+field.upper()+"_MISSING_OR_INVALID")
        data[field]={n:float(x) for n,x in zip(names,positions)}
    header=msg.header.stamp
    data["stamp"]=float(header.sec)+float(header.nanosec)*1e-9
    return data

def accept_real_finger_state(action_status,action_result_code,measured,goal,
                             controller_samples,stamp_after,stamp_before):
    if action_status!=4 or action_result_code!=0:
        return "ACTION_NOT_SUCCEEDED"
    if not controller_samples:
        return "CONTROLLER_TRACE_ABSENT"
    last=controller_samples[-1]
    if last["stamp"]<stamp_before or last["stamp"]>stamp_after+.5:
        return "CONTROLLER_TRACE_STALE"
    for joint in FINGERS:
        if joint not in measured or not math.isfinite(measured[joint]):
            return "INDEPENDENT_JOINT_STATE_MISSING"
        if abs(measured[joint]-goal[joint])>TOLERANCE_M:
            return "REAL_JOINT_NOT_AT_GOAL_"+joint
        if abs(last["reference"][joint]-goal[joint])>TOLERANCE_M:
            return "REFERENCE_NOT_AT_GOAL_"+joint
        if abs(last["feedback"][joint]-measured[joint])>.002:
            return "CONTROLLER_FEEDBACK_JOINT_STATE_DIVERGENCE_"+joint
    return "FREE_SPACE_ACTUATION_SCOPED_PASS"
