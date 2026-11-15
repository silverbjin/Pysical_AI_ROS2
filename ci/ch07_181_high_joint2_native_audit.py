#!/usr/bin/env python3
"""Issue #181: read-only, source-stamped high MoveGroup / joint2 causal evidence.

Never treat absence of hardware introspection or ECS as a zero command.
Never mark G04B physically accepted from this diagnostic.
"""
import csv,json,math,sys
from pathlib import Path

def inspect(receipt,rows):
    out={"G00_G04A":"NOT_RERUN","G04B":"BLOCKED","G05":"NOT_RUN",
         "Ch10":"HOLD","scope":"HIGH_MOVEGROUP_JOINT2_CAUSAL_READ_ONLY",
         "verdict":"UNKNOWN_UNOBSERVED"}
    evidence=receipt.get("last_high_joint2_causal_even_on_failure")
    if not isinstance(evidence,dict):
        out["verdict"]="HIGH_MOVEGROUP_CAUSAL_WINDOW_MISSING"
        return out
    begin,end=evidence.get("start_sim_s"),evidence.get("end_sim_s")
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (begin,end)) or end<begin:
        out["verdict"]="INVALID_SIM_TIME_WINDOW";return out
    jtc=[s for s in evidence.get("jtc_reference_feedback_error",[])
         if begin<=s.get("stamp",-1)<=end]
    hw=[s for s in evidence.get("hardware_command_position",[])
        if begin<=s.get("stamp",-1)<=end
        and s.get("name")=="command_interface.joint2/position"]
    all_ecs=list(rows)
    ecs=[]
    for s in all_ecs:
        try:
            if s["joint_name"]=="joint2" and s["phase"] in ("pre","post") and begin<=float(s["sim_time_s"])<=end:
                ecs.append(s)
        except (KeyError,ValueError,TypeError):pass
    def numeric(rows,field):
        values=[]
        for s in rows:
            try:
                v=float(s[field])
                if math.isfinite(v):values.append(v)
            except (KeyError,TypeError,ValueError):pass
        return values
    references=numeric(jtc,"reference_joint2_rad")
    feedback=numeric(jtc,"feedback_joint2_rad")
    actual_hw=numeric(hw,"position_rad")
    pre_cmd=numeric([s for s in ecs if s["phase"]=="pre"],"velocity_cmd_mps")
    # The last 0.2..0.7s AFTER MoveGroup returns exposes persistent
    # velocity commands while DART native motion has plateaued. Prior
    # implementation incorrectly treated .is_limited=0 as position command.
    late=[]
    for s in all_ecs:
        try:
            if (s["joint_name"]=="joint2" and s["phase"]=="pre"
                    and end+.2<=float(s["sim_time_s"])<=end+.7):
                late.append(s)
        except (KeyError,ValueError,TypeError):pass
    late_command=numeric(late,"velocity_cmd_mps")
    late_velocity=numeric(late,"velocity_mps")
    late_position=numeric(late,"position_m")
    native_positions=numeric(ecs,"position_m")
    rec={"start_sim_s":begin,"end_sim_s":end,
         "jtc_count":len(jtc),"hardware_count":len(hw),"native_ecs_count":len(ecs),
         "hardware_names":sorted({v["name"] for v in hw}),
         "jtc_reference_first_last":[references[0],references[-1]] if references else None,
         "jtc_feedback_first_last":[feedback[0],feedback[-1]] if feedback else None,
         "hardware_first_last":[actual_hw[0],actual_hw[-1]] if actual_hw else None,
         "native_pre_velocity_abs_peak_rad_s":max(map(abs,pre_cmd),default=None),
         "native_position_first_last":[native_positions[0],native_positions[-1]] if native_positions else None,
         "native_position_range_rad":max(native_positions)-min(native_positions) if native_positions else None,
         "controller_observer_errors":evidence.get("observer_errors",[]),
         "late_window_after_goal_s":[end+.2,end+.7],
         "late_native_sample_count":len(late),
         "late_velocity_command_abs_median_rad_s":(
             sorted(map(abs,late_command))[len(late_command)//2] if late_command else None),
         "late_actual_velocity_abs_median_rad_s":(
             sorted(map(abs,late_velocity))[len(late_velocity)//2] if late_velocity else None),
         "late_native_joint2_position_span_rad":(
             max(late_position)-min(late_position) if late_position else None)}

    out["measurements"]=rec
    if not references:out["verdict"]="JTC_REFERENCE_UNOBSERVED"
    elif not actual_hw:out["verdict"]="HARDWARE_COMMAND_UNOBSERVED"
    elif not pre_cmd:out["verdict"]="NATIVE_PRE_PHYSICS_COMMAND_UNOBSERVED"
    elif not native_positions:out["verdict"]="NATIVE_JOINT_POSITION_UNOBSERVED"
    elif (max(map(abs,pre_cmd))>=.001 and
          (max(native_positions)-min(native_positions))<.0005):
        out["verdict"]="HIGH_JOINT2_NONZERO_NATIVE_CMD_BUT_FROZEN"
    elif (len(late)>=8 and len(late_command)>=8
          and len(late_velocity)>=8 and len(late_position)>=8
          and rec["late_velocity_command_abs_median_rad_s"]>.05
          and rec["late_actual_velocity_abs_median_rad_s"]<.001
          and rec["late_native_joint2_position_span_rad"]<.0005):
        out["verdict"]="HIGH_JOINT2_POST_RESULT_NATIVE_STALL_WITH_NONZERO_CMD"
    else:out["verdict"]="HIGH_JOINT2_NATIVE_MOTION_PRESENT_CHECK_TRACKING_AND_CONSTRAINT"
    return out

def main(receipt_path,csv_path,out_path):
    result={"G04B":"BLOCKED","G05":"NOT_RUN","Ch10":"HOLD",
            "verdict":"RECEIPT_OR_ECS_FILE_MISSING"}
    if Path(receipt_path).is_file() and Path(csv_path).is_file():
        with open(csv_path,newline="") as f:
            result=inspect(json.loads(Path(receipt_path).read_text()),csv.DictReader(f))
    Path(out_path).write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("G04B_181_HIGH_JOINT2_CAUSAL="+result["verdict"],"G04B=BLOCKED",flush=True)
    return result
if __name__=="__main__":
    if len(sys.argv)!=4:raise SystemExit("usage: high_audit.py <receipt.json> <native_ecs.csv> <output.json>")
    main(*sys.argv[1:])
