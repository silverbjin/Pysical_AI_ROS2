#!/usr/bin/env python3
"""Issue #181 Cycle04: lower-joint3 ROS→hardware→native observability only.

Always BLOCKED; classify actual simulator evidence, not nominal actuator success.
The CSV is read-only and includes pre-/post-physics records and other joints.
"""
import csv,json,math,statistics,sys
from pathlib import Path
JOINT="joint3"
EXACT_HW="command_interface.joint3/position"

def valid_float(value):
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None

def inspect_window(window,rows):
    result={"verdict":"UNKNOWN_INCOMPLETE_NATIVE_EVIDENCE"}
    if not isinstance(window,dict):return result
    start,end=valid_float(window.get("start_sim_s")),valid_float(window.get("end_sim_s"))
    if start is None or end is None or end<start:return result
    ref=[x for x in window.get("jtc_reference_feedback_error",[])
         if start<=x.get("stamp",-1)<=end]
    hw=[x for x in window.get("hardware_command_position",[])
        if x.get("name")==EXACT_HW and start<=x.get("stamp",-1)<=end]
    actual=[x for x in rows if x.get("joint_name")==JOINT and
            x.get("phase") in ("pre","post") and
            (valid_float(x.get("sim_time_s")) is not None) and
            start<=float(x["sim_time_s"])<=end]
    pre=[x for x in actual if x["phase"]=="pre"]
    def nums(seq,key):
        return [v for x in seq if (v:=valid_float(x.get(key))) is not None]
    rref=nums(ref,"reference_joint3_rad")
    rfeedback=nums(ref,"feedback_joint3_rad")
    cmd=nums(hw,"position_rad")
    speed=nums(pre,"velocity_cmd_mps")
    pos=nums(actual,"position_m")
    tail=[x for x in pre if end-.5<=float(x["sim_time_s"])<=end-.05]
    tcmd=nums(tail,"velocity_cmd_mps")
    tvel=nums(tail,"velocity_mps")
    tpos=nums(tail,"position_m")
    goal=valid_float(window.get("goal_joint3_rad"))
    observed=valid_float(window.get("actual_joint3_rad"))
    measurements={"start_sim_s":start,"end_sim_s":end,
                  "reference_samples":len(rref),"hw_command_samples":len(cmd),
                  "native_pre_samples":len(pre),
                  "reference_first_last":[rref[0],rref[-1]] if rref else None,
                  "feedback_first_last":[rfeedback[0],rfeedback[-1]] if rfeedback else None,
                  "hw_first_last":[cmd[0],cmd[-1]] if cmd else None,
                  "native_position_first_last":[pos[0],pos[-1]] if pos else None,
                  "native_position_span_rad":max(pos)-min(pos) if pos else None,
                  "native_pre_velocity_command_abs_peak_rad_s":max(map(abs,speed),default=None),
                  "tail_sample_count":len(tail),
                  "tail_cmd_abs_median_rad_s":statistics.median(map(abs,tcmd)) if tcmd else None,
                  "tail_real_velocity_abs_median_rad_s":statistics.median(map(abs,tvel)) if tvel else None,
                  "tail_native_position_span_rad":max(tpos)-min(tpos) if tpos else None,
                  "goal_rad":goal,"observed_actual_rad":observed,
                  "actual_goal_error_rad":abs(goal-observed) if goal is not None and observed is not None else None,
                  "controller_observer_errors":window.get("observer_errors",[])}
    result["measurements"]=measurements
    if len(rref)<8:result["verdict"]="JTC_REFERENCE_MISSING_OR_TOO_FEW_SAMPLES"
    elif len(cmd)<8:result["verdict"]="HARDWARE_POSITION_COMMAND_MISSING"
    elif len(speed)<8 or len(pos)<8:result["verdict"]="NATIVE_ECS_COMMAND_OR_POSITION_MISSING"
    elif (len(tail)>=8 and len(tcmd)>=8 and len(tvel)>=8 and len(tpos)>=8
          and measurements["tail_cmd_abs_median_rad_s"]>.05
          and measurements["tail_real_velocity_abs_median_rad_s"]<.001
          and measurements["tail_native_position_span_rad"]<.0005):
        result["verdict"]="LOWER_JOINT3_NATIVE_STALL_WITH_NONZERO_COMMAND"
    else:result["verdict"]="LOWER_JOINT3_COMMAND_AND_MOTION_PRESENT_REVIEW_CONSTRAINT"
    return result

def inspect(receipt,rows):
    out={"G04B":"BLOCKED","G05":"NOT_RUN","Ch10":"HOLD",
         "scope":"LOWER_JOINT3_NATIVE_COMMAND_FIRST_BOUNDARY",
         "verdict":"UNKNOWN_NO_LOWER_GOAL"}
    if not isinstance(receipt,dict):return out
    all_rows=list(rows)
    lower=receipt.get("last_lower_joint3_causal_even_on_failure")
    if not isinstance(lower,dict):return out
    out["movegroup"]=inspect_window(lower,all_rows)
    settle=receipt.get("last_arm_settle_even_on_failure",{})
    if (isinstance(settle,dict)
            and isinstance(settle.get("joint3_observation_window"),dict)
            and settle.get("desired",{}).get("joint3")==lower.get("goal_joint3_rad")):
        out["strict_fjt"]=inspect_window(settle["joint3_observation_window"],all_rows)
        out["strict_fjt"]["action_status"]=settle.get("action_status")
        out["strict_fjt"]["result_error"]=settle.get("result_error")
    else:
        out["strict_fjt"]={"verdict":"NOT_RUN_OR_DIFFERENT_GOAL"}
    out["verdict"]="READ_ONLY_CAUSAL_WINDOWS_PRESERVED_NOT_G04B_PASS"
    return out

def main(receipt_path,ecs_path,out_path):
    out={"G04B":"BLOCKED","G05":"NOT_RUN","Ch10":"HOLD",
         "verdict":"RECEIPT_OR_NATIVE_ECS_FILE_MISSING"}
    if Path(receipt_path).is_file() and Path(ecs_path).is_file():
        with open(ecs_path,newline="") as f:
            out=inspect(json.loads(Path(receipt_path).read_text()),csv.DictReader(f))
    Path(out_path).write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print("G04B_181_LOWER_JOINT3_CAUSAL="+out["verdict"],"G04B=BLOCKED",flush=True)
    return out

if __name__=="__main__":
    if len(sys.argv)!=4:
        raise SystemExit("usage: lower_joint3_native_audit.py <receipt.json> <native_ecs.csv> <out.json>")
    main(*sys.argv[1:])
