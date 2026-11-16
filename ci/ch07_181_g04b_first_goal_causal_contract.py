#!/usr/bin/env python3
"""#181 evidence-only: classify first G04B finger-goal command boundary.

A controller_state sample AFTER FJT abort often resets reference to actual.
Only in-window reference/feedback and explicitly named hardware command
interfaces may establish the causal chain. Never infer Gazebo physics PASS.
"""
import math
FINGERS=("joint_finger1","joint_finger2")
TARGET_M=.002
EPS_M=.0005

def first_goal_evidence(controller_samples,hardware_samples,actual,goal_start_s,
                        goal_end_s,target_m=TARGET_M):
    if not isinstance(actual,dict) or set(actual)!=set(FINGERS):
        raise ValueError("G04B_181_ACTUAL_JOINT_KEYS_REQUIRED")
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in actual.values()):
        raise ValueError("G04B_181_INVALID_ACTUAL")
    if not (math.isfinite(goal_start_s) and math.isfinite(goal_end_s)
            and goal_end_s>=goal_start_s and 0<target_m<=.025):
        raise ValueError("G04B_181_INVALID_GOAL_TIME_OR_TARGET")
    rows=[]
    for s in controller_samples:
        try:
            names=s["names"]
            t=float(s["stamp"])
            ref=s["reference"];feedback=s["feedback"];error=s["error"]
            valid=(list(names)==list(FINGERS)
                and all(len(z)==2 and all(math.isfinite(float(v)) for v in z)
                        for z in (ref,feedback,error)))
        except (ValueError,TypeError,KeyError,OverflowError):
            continue
        if valid and goal_start_s<=t<=goal_end_s:
            rows.append(s)
    command_peaks={n:None for n in FINGERS}
    hardware_window=[]
    for s in hardware_samples:
        try:
            t=float(s["sim_observed_s"])
            values=s["values"]
        except (KeyError,TypeError,ValueError):
            continue
        if not goal_start_s<=t<=goal_end_s or not isinstance(values,dict):
            continue
        relevant={}
        for key,value in values.items():
            if "command" not in key.lower() or "position" not in key.lower():
                continue
            for n in FINGERS:
                if n in key and isinstance(value,(int,float)) and math.isfinite(value):
                    relevant[key]=float(value)
                    command_peaks[n]=max(
                        value,command_peaks[n] if command_peaks[n] is not None
                        else -math.inf)
        if relevant:hardware_window.append({"stamp":t,"values":relevant})
    peaks={}
    for i,n in enumerate(FINGERS):
        ref_peak=max((float(s["reference"][i]) for s in rows),default=None)
        fb_peak=max((float(s["feedback"][i]) for s in rows),default=None)
        err_peak=max((abs(float(s["error"][i])) for s in rows),default=None)
        if ref_peak is None or ref_peak<target_m-EPS_M:
            stage="JTC_REFERENCE_UNOBSERVED"
        elif actual[n]>=target_m-EPS_M:
            stage="PHYSICAL_JOINT_REACHED_SCOPED"
        elif command_peaks[n] is None:
            stage="JTC_GOAL_REACHED_HARDWARE_UNOBSERVED"
        elif command_peaks[n]<target_m-EPS_M:
            stage="JTC_TO_HARDWARE_COMMAND_GAP"
        else:
            stage="HARDWARE_COMMAND_PRESENT_NATIVE_GAZEBO_UNCLASSIFIED"
        peaks[n]={"reference_peak_m":ref_peak,"feedback_peak_m":fb_peak,
                  "error_abs_peak_m":err_peak,"actual_final_m":float(actual[n]),
                  "hardware_command_peak_m":command_peaks[n],
                  "first_known_boundary":stage}
    return {"contract":"G04B_181_FIRST_FINGER_GOAL_CAUSAL_RECEIPT",
            "target_m":target_m,"goal_start_sim_s":goal_start_s,
            "goal_end_sim_s":goal_end_s,"controller_samples_in_goal":len(rows),
            "hardware_command_samples_in_goal":len(hardware_window),
            "hardware_command_names":sorted({k for row in hardware_window
                                              for k in row["values"]}),
            "finger_results":peaks,"gazebo_joint_velocity_cmd":"NOT_IN_THIS_RECEIPT_READ_ECS_CSV",
            "G04B":"BLOCKED_UNTIL_NATIVE_PHYSICAL_ACCEPTANCE","G05":"NOT_RUN"}
