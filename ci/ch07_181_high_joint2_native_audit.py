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
        if begin<=s.get("stamp",-1)<=end and "joint2" in s.get("name","")]
    ecs=[]
    for s in rows:
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
         "controller_observer_errors":evidence.get("observer_errors",[])}
    out["measurements"]=rec
    if not references:out["verdict"]="JTC_REFERENCE_UNOBSERVED"
    elif not actual_hw:out["verdict"]="HARDWARE_COMMAND_UNOBSERVED"
    elif not pre_cmd:out["verdict"]="NATIVE_PRE_PHYSICS_COMMAND_UNOBSERVED"
    elif not native_positions:out["verdict"]="NATIVE_JOINT_POSITION_UNOBSERVED"
    elif (max(map(abs,pre_cmd))>=.001 and
          (max(native_positions)-min(native_positions))<.0005):
        out["verdict"]="HIGH_JOINT2_NONZERO_NATIVE_CMD_BUT_FROZEN"
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
