#!/usr/bin/env python3
"""Issue #181: independent read-only ECS csv + real controller receipt correlation."""
import csv,json,math,sys
from pathlib import Path
def parse_ecs_csv(path):
    if not Path(path).exists():
        return {"status":"ECS_TRACE_NOT_CREATED","rows":0}
    with open(path,newline="") as file:
        rows=list(csv.DictReader(file))
    if not rows:
        return {"status":"ECS_TRACE_EMPTY","rows":0}
    required={"sim_time_s","phase","joint_entity","velocity_cmd_present",
              "velocity_cmd_size","velocity_cmd_mps",
              "position_m","velocity_mps","force_cmd_present"}
    if not required.issubset(rows[0]):
        return {"status":"ECS_TRACE_INVALID_SCHEMA","rows":len(rows)}
    return {"status":"ECS_ROWS_PRESENT","rows":len(rows),"data":rows}

def summarize(rows,before,after):
    relevant=[r for r in rows if before<=float(r["sim_time_s"])<=after]
    if not relevant:
        return {"status":"NO_ECS_ROWS_IN_FJT_GOAL","rows":0}
    result={"status":"ECS_GOAL_SAMPLES","rows":len(relevant),
            "by_phase":{}}
    for phase in ("pre","post"):
        obs=[r for r in relevant if r["phase"]==phase]
        def numbers(key):
            return [v for r in obs if math.isfinite(v:=float(r[key]))]
        cmd=numbers("velocity_cmd_mps")
        pos=numbers("position_m")
        vel=numbers("velocity_mps")
        result["by_phase"][phase]={
            "rows":len(obs),
            "joint_entity_ids":sorted({r["joint_entity"] for r in obs}),
            "velocity_cmd_component_seen":any(r["velocity_cmd_present"]=="1" for r in obs),
            "velocity_cmd_vector_populated":any(int(r["velocity_cmd_size"])>0 for r in obs),
            "velocity_cmd_max_abs_mps":max(map(abs,cmd),default=None),
            "velocity_cmd_nonzero_samples":sum(abs(v)>.0005 for v in cmd),
            "native_joint_position_max_abs_m":max(map(abs,pos),default=None),
            "native_joint_velocity_max_abs_mps":max(map(abs,vel),default=None),
            "force_cmd_component_seen":any(r["force_cmd_present"]=="1" for r in obs)}
    return result

def classify(audit,hardware_command_peak,hardware_state_peak):
    if audit.get("status")!="ECS_GOAL_SAMPLES":
        return "ECS_UNOBSERVED_CAUSE_UNDETERMINED"
    if hardware_command_peak<.0105:
        return "HW_COMMAND_NOT_PROVEN"
    if hardware_state_peak>.001:
        return "HW_PHYSICAL_STATE_MOVED"
    phase=audit["by_phase"]
    vals=[v for row in phase.values() if
          row["velocity_cmd_component_seen"]
          for v in [row["velocity_cmd_max_abs_mps"]] if v is not None]
    if any(v>.0005 for v in vals):
        return "ECS_NONZERO_VELOCITY_CMD_WHILE_NATIVE_JOINT_FROZEN"
    # Gazebo physics can clear command components between Pre/Post observations.
    # Never equate *unobserved* with *never written*.
    return "ECS_NONZERO_CMD_NOT_OBSERVED_AT_SAMPLED_PHASES"

def generate(csv_path,witness_path,out_path):
    ecs=parse_ecs_csv(csv_path)
    report={"scope":"ISSUE_181_READ_ONLY_GAZEBO_ECS_CAUSAL_AUDIT",
            "G00_G04A":"NOT_RERUN","G04B":"BLOCKED","G05":"NOT_RUN",
            "Ch10":"HOLD","ecs_file":str(csv_path)}
    report.update({k:v for k,v in ecs.items() if k!="data"})
    if not Path(witness_path).exists():
        report["verdict"]="WITNESS_RECEIPT_MISSING"
    else:
        witness=json.loads(Path(witness_path).read_text())
        goals=witness.get("per_goal_results",[])
        if not goals:
            report["verdict"]="FJT_GOAL_NOT_COMPLETED"
        else:
            goal=goals[-1]
            report["goal_name"]=goal.get("label")
            report["before_sim_s"]=goal.get("before_stamp")
            report["after_sim_s"]=goal.get("after_stamp")
            hw=goal.get("hardware_command_peak_candidates",{})
            report["hardware_position_command_peak_m"]=max(hw.values(),default=None)
            measured=goal.get("measured_fingers",{})
            report["finger2_ros_joint_actual_m"]=measured.get("joint_finger2")
            if ecs.get("status")=="ECS_ROWS_PRESENT":
                summary=summarize(ecs["data"],goal["before_stamp"],goal["after_stamp"])
                report["goal_ecs"]=summary
                if report["hardware_position_command_peak_m"] is not None:
                    report["verdict"]=classify(
                        summary,report["hardware_position_command_peak_m"],
                        abs(report["finger2_ros_joint_actual_m"] or 0.0))
                else:
                    report["verdict"]="HARDWARE_COMMAND_UNOBSERVED"
            else: report["verdict"]="ECS_PLUGIN_TRACE_UNOBSERVED"
    Path(out_path).write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report

if __name__=="__main__":
    if len(sys.argv)!=4:raise SystemExit("usage: audit.py <ecs.csv> <witness.json> <out.json>")
    result=generate(*map(Path,sys.argv[1:]))
    print("CH07_181_ECS_AUDIT verdict="+result.get("verdict","UNKNOWN")+" rows="+str(result["rows"]))
