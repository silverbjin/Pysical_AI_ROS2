#!/usr/bin/env python3
"""Read-only, fail-closed Issue #181 real-command -> Gazebo physical-state witness."""
import math,re

FINGER2="joint_finger2"
def relevant_introspection_pairs(statistics):
    """Statistics.statistics is a list of pal_statistics_msgs/Statistic records.
    Preserve original names; never assume that similarly named state and
    command interfaces are interchangeable.
    """
    result={}
    for entry in statistics:
        name=str(getattr(entry,"name",""))
        try:
            v=float(getattr(entry,"value"))
        except (ValueError,TypeError,AttributeError):
            continue
        if any(k in name for k in ("joint_finger1","joint_finger2")) and math.isfinite(v):
            result[name]=v
    return result

def explicit_command_peaks(samples,joint="joint_finger2"):
    found={}
    for sample in samples:
        for name,value in sample.get("values",{}).items():
            # ros2_control registry labels differentiate command vs state.
            # Do not treat a bare joint/position name as proof of COMMAND.
            if joint in name and "command" in name.lower():
                found[name]=max(found.get(name,float("-inf")),float(value))
    return found

def native_link_xyz(raw,link):
    """Parse world xyz of Gazebo's link (not its inertial origin)."""
    # Keep the full model output, including metadata, in the original ZIP.
    text=raw.split("- Name: "+link,1)
    if len(text)!=2:return None
    pattern=r"(?m)^\s*- Pose \[ XYZ \(m\) \] \[ RPY \(rad\) \]:\s*\n\s*\[([^\]]+)\]"
    m=re.search(pattern,text[1])
    if not m:return None
    try:values=tuple(float(s) for s in m.group(1).split())
    except ValueError:return None
    return values if len(values)==3 and all(math.isfinite(x) for x in values) else None

def classify_chain(reference_max,feedback_max,command_peaks,native_delta,goal=.011):
    if not (math.isfinite(reference_max) and math.isfinite(feedback_max)):
        return "INVALID_JTC_EVIDENCE"
    if reference_max < goal-.0005:
        return "GOAL_TO_JTC_REFERENCE_GAP"
    if feedback_max >= goal-.001:
        return "FINGER_ACTUAL_MOVED"
    if not command_peaks:
        return "JTC_REFERENCE_REACHED_BUT_HARDWARE_COMMAND_UNOBSERVED"
    if max(command_peaks.values()) < goal-.0005:
        return "JTC_REFERENCE_TO_HARDWARE_COMMAND_GAP"
    if native_delta is None:
        return "COMMAND_PRESENT_NATIVE_GAZEBO_UNOBSERVED"
    if native_delta <=.0005:
        return "COMMAND_PRESENT_BUT_NATIVE_GAZEBO_JOINT_DID_NOT_MOVE"
    return "NATIVE_LINK_MOVED_BUT_ROS_JOINTSTATE_FROZEN"
