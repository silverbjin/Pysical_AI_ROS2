#!/usr/bin/env python3
"""#181 read-only receipt/dual-finger ECS corroborator; NEVER physical PASS."""
import csv,json,math,sys
from pathlib import Path
FINGERS=("joint_finger1","joint_finger2")

def audit(first_goal,ecs_rows):
    if not isinstance(first_goal,dict) or not first_goal.get("first_goal_causal_receipt"):
        return {"G04B":"BLOCKED","verdict":"FIRST_GOAL_CAUSAL_EVIDENCE_MISSING"}
    causal=first_goal["first_goal_causal_receipt"]
    start=causal["goal_start_sim_s"];end=causal["goal_end_sim_s"]
    if not (isinstance(start,(int,float)) and isinstance(end,(int,float))
            and math.isfinite(start) and math.isfinite(end) and start<=end):
        return {"G04B":"BLOCKED","verdict":"INVALID_FJT_GOAL_INTERVAL"}
    result={"G04B":"BLOCKED","G05":"NOT_RUN","Ch10":"HOLD",
            "scope":"FIRST_FINGER_GOAL_NATIVE_ECS_READONLY",
            "source_causal_receipt":causal,
            "joint_ecs":{},"verdict":"UNKNOWN"}
    all_ecs_rows=list(ecs_rows)
    for name in FINGERS:
        rows=[]
        for row in all_ecs_rows:
            try:
                if row["joint_name"]!=name:continue
                t=float(row["sim_time_s"])
                if not start<=t<=end:continue
                if row["phase"] not in ("pre","post"):continue
            except (ValueError,TypeError,KeyError):
                continue
            rows.append(row)
        def finite(key,phase=None):
            vals=[]
            for row in rows:
                if phase is not None and row["phase"]!=phase:continue
                try:
                    v=float(row[key])
                    if math.isfinite(v):vals.append(v)
                except (KeyError,ValueError,TypeError):
                    pass
            return vals
        pre=finite("velocity_cmd_mps","pre")
        post=finite("velocity_cmd_mps","post")
        positions=finite("position_m")
        hw=causal["finger_results"].get(name,{})
        delta=(max(positions)-min(positions)) if positions else None
        cmd_peak=max((abs(v) for v in pre+post),default=None)
        first_boundary=hw.get("first_known_boundary","UNKNOWN")
        if not rows:
            verdict="NATIVE_ECS_UNOBSERVED"
        elif (first_boundary=="JTC_REFERENCE_UNOBSERVED"):
            verdict="JTC_REFERENCE_UNOBSERVED_DO_NOT_INFER_HARDWARE"
        elif delta is None:
            verdict="NATIVE_POSITION_UNOBSERVED"
        elif cmd_peak is not None and cmd_peak>.0005 and delta<.0005:
            verdict="ECS_NONZERO_CMD_BUT_NATIVE_JOINT_FROZEN"
        elif delta>=.0005:
            verdict="NATIVE_JOINT_MOVED_SCOPED"
        elif cmd_peak is None or cmd_peak<=.0005:
            verdict="NONZERO_ECS_CMD_NOT_OBSERVED_CAUSE_UNKNOWN"
        else:
            verdict="UNCLASSIFIED"
        result["joint_ecs"][name]={
            "rows":len(rows),"pre_cmd_samples":len(pre),
            "post_cmd_samples":len(post),
            "max_abs_pre_velocity_cmd_mps":max(map(abs,pre),default=None),
            "max_abs_post_velocity_cmd_mps":max(map(abs,post),default=None),
            "native_joint_position_samples":len(positions),
            "native_joint_position_range_m":delta,
            "hardware_position_command_peak_m":hw.get("hardware_command_peak_m"),
            "jtc_reference_peak_m":hw.get("reference_peak_m"),
            "measured_final_m":hw.get("actual_final_m"),
            "first_boundary":verdict}
    failed=first_goal.get("actual_m",{})
    stalled=[n for n in FINGERS if isinstance(failed.get(n),(float,int))
             and abs(failed[n]-.002)>.0005]
    result["stalled_joints"]=stalled
    result["verdict"]=("READONLY_CAUSAL_CHAIN_RECORDED_G04B_STILL_BLOCKED"
                       if all(result["joint_ecs"][n]["rows"] for n in FINGERS)
                       else "INCOMPLETE_NATIVE_ECS_EVIDENCE_G04B_STILL_BLOCKED")
    return result

def main(receipt_path,ecs_path,out_path):
    output={"G04B":"BLOCKED","G05":"NOT_RUN","Ch10":"HOLD",
            "verdict":"FIRST_GOAL_OR_NATIVE_ECS_MISSING"}
    if Path(receipt_path).is_file() and Path(ecs_path).is_file():
        source=json.loads(Path(receipt_path).read_text())
        goal=source.get("last_gripper_result_even_on_failure")
        if goal and goal.get("name") in ("lower_stop_release_finger1_only_2mm",
                                           "lower_stop_release_both_fingers_2mm"):
            with open(ecs_path,newline="") as fh:
                output=audit(goal,csv.DictReader(fh))
    Path(out_path).write_text(json.dumps(output,indent=2,allow_nan=False)+"\n")
    print("G04B_181_FIRST_FINGER_CAUSAL_AUDIT="+output["verdict"],
          "G04B=BLOCKED",flush=True)
    return output

if __name__=="__main__":
    if len(sys.argv)!=4:
        raise SystemExit("usage: audit.py <physical_receipt> <native_finger_ecs.csv> <out.json>")
    main(*sys.argv[1:])
