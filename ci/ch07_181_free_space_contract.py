#!/usr/bin/env python3
"""Issue #181: fail-closed, ROS-independent interpretation of Jazzy JTC traces.

The accepted G04B source was reading obsolete .desired/.actual fields; Jazzy
control_msgs/JointTrajectoryControllerState publishes .reference/.feedback/.error.
This module never infers physical movement from FJT Action success alone.
"""
import math

FINGERS=("joint_finger1","joint_finger2")
GOAL_M=0.012
TOLERANCE_M=0.001

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
