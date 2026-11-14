#!/usr/bin/env python3
"""Independent posthoc Gazebo native gz.msgs.Contacts and world-pose audit.

A MoveGroup/FJT SUCCEEDED result cannot demonstrate real physical grasp.
Count *both* original finger collision pairs with dynamic rod and force,
plus independent real Gazebo rod poses showing lift, 1.3s hold and release.
"""
import hashlib,json,math,re,sys
from pathlib import Path
raw_path,physical_path,out_path,support_path=map(Path,sys.argv[1:5])
raw=raw_path.read_text(errors="replace")
support_native=support_path.read_bytes()
support_wrist_mentions=support_native.count(
    b"my_robot::link_wrist::link_wrist_collision")
support_rod_mentions=support_native.count(
    b"g04_grasp_cylinder::cylinder_link::cylinder_collision")
result=json.loads(physical_path.read_text())

def blocks(text,tag):
    pat=re.compile(r"\b"+re.escape(tag)+r"\s*\{")
    pos=0
    while (m:=pat.search(text,pos)) is not None:
        start=m.end()-1; depth=0
        for end in range(start,len(text)):
            if text[end]=="{":depth+=1
            elif text[end]=="}":
                depth-=1
                if depth==0:
                    yield text[start+1:end]
                    pos=end+1
                    break
        else: break


def nfield(text,key):
    m=re.search(r"\b"+re.escape(key)+r"\s*:\s*([-+\d.eE]+)",text)
    return float(m.group(1)) if m else None

contacts={"finger1":[], "finger2":[]}
total=0
for b in blocks(raw,"contact"):
    total+=1
    names=[]
    for tag in ("collision1","collision2"):
        sub=next(iter(blocks(b,tag)),"")
        m=re.search(r'\bname\s*:\s*"([^"]+)"',sub)
        names.append(m.group(1) if m else "")
    if not any("g04_grasp_cylinder" in x for x in names):continue
    forces=[]
    for part in blocks(b,"force"):
        xyz=[nfield(part,d) for d in ("x","y","z")]
        if all(v is not None and math.isfinite(v) for v in xyz):
            forces.append(math.sqrt(sum(v*v for v in xyz)))
    for f in contacts:
        if any("my_robot" in x and f in x for x in names):
            contacts[f].append({"pair":names,"max_force_N":max(forces) if forces else None})
summary={k:{
    "contact_events":len(v),
    "positive_contact_force_count":sum(x["max_force_N"] is not None and
                                    x["max_force_N"]>1e-4 for x in v),
    "max_native_force_N":max((x["max_force_N"] for x in v
                            if x["max_force_N"] is not None),default=None),
    "first_collision_pair":v[0]["pair"] if v else None
} for k,v in contacts.items()}
p=result.get("pose_snapshots",{})
conditions={
 "native_raw_contact_blocks":total>0,
 "new_native_support_sensor_stream_present":len(support_native)>1000 and support_rod_mentions>=3,
 "no_wrist_support_collision_in_entire_trajectory":support_wrist_mentions==0,
 "real_both_fingers_at_least_three_contacts":all(v["contact_events"]>=3 for v in summary.values()),
 "real_both_fingers_positive_force":all(v["positive_contact_force_count"]>=1 for v in summary.values()),
 "real_dynamic_world_lift_at_least_0_05m":result.get("lift_m",-1)>=.05,
 "1_3s_hold_pose_drift_le_0_025m":result.get("object_pose_drift_during_hold_m",1) <=.025,
 "placement_xy_error_le_0_09m":result.get("placement_xy_error_m",1)<=.09,
 "placement_height_error_le_0_055m":result.get("placement_center_height_error_m",1)<=.055,
 "one_actual_moving_rod_sequence":all(k in p for k in
                  ("initial","pregrasp","approach","closed","lift","held","pre_release","settled")),
 "actual_arm_movegroup_and_gripper_fjt_sequence":(
         4<=result.get("arm_goal_count",-1)<=13 and
         result.get("finger_goal_count")==4 and
         len(result.get("arm_results",[]))==result.get("arm_goal_count",0)+2 and
         len(result.get("finger_results",[]))==4 and
         result.get("free_space_diagnostics_all_tracking_pass") is True and
         len(result.get("finger_clearance_preflight",[]))==7 and
         "contact_close_stage1" in [g.get("name") for g in result.get("finger_results",[])] and
         result.get("preclose_object_shift_m",1)<=.018 and
         result.get("aligned_pregrasp_radius_error_m",1)<=.005 and
         "aligned_pregrasp" in p and
         all(v.get("name","").startswith(("pregrasp","x_approach_",
                                         "fine_x_alignment_","lift","transfer","grasp"))
             for v in result.get("arm_results",[])) and
         result.get("rod_shift_before_close_at_yaw_stage_m",1)<=.012 and
         "x_clearance_stage" in p and
         "x_approach_insertion" in [a.get("name") for a in result.get("arm_results",[])] and
         result.get("approach_axis")=="WORLD_X_INSERTION_FINGER_SEPARATION_WORLD_Y" and
         result.get("native_open_finger_separation_world_m",{}).get("dy",0)>=.054 and
         result.get("native_open_finger_separation_world_m",{}).get("dz",1)<=.010),
 "original_g04a_visual_stage_not_replayed":(
         result.get("g04a_old_live_xyz_replayed_as_current") is False
         and result.get("G05_integrated_live_perception")=="NOT_RUN"),
 "ch10_hold":result.get("Ch10")=="HOLD",
 "physical_fixture_no_forced_attachment":result.get("fixture",{}).get("no_forced_attachment") is True
}
passed=(all(conditions.values())
        and result.get("status")=="CANDIDATE_PASS_PENDING_INDEPENDENT_NATIVE_CONTACT_AUDIT")
receipt={"scope":"G04B_NATIVE_GZ_MSGS_CONTACTS_PLUS_REAL_GZ_MODEL_POSE",
         "status":"PASS" if passed else "FAIL",
         "native_raw_sha256":hashlib.sha256(raw_path.read_bytes()).hexdigest(),
         "native_raw_bytes":raw_path.stat().st_size,
         "native_support_raw_sha256":hashlib.sha256(support_native).hexdigest(),
         "native_support_raw_bytes":len(support_native),
         "native_support_rod_mentions":support_rod_mentions,
         "native_support_wrist_collision_mentions":support_wrist_mentions,
         "total_contact_blocks":total,
         "per_finger":summary,"checks":conditions,
         "original_goal_provenance":"NEW_G04B_PHYSICS_FIXTURE_NOT_G04A_SENSOR_REPLAY",
         "G05_live_rgbd_full_chain":"NOT_RUN",
         "Ch10":"HOLD"}
out_path.write_text(json.dumps(receipt,indent=2)+"\n")
print("CH07_77_G04B_ACTUAL_BILATERAL_ROD_CONTACT_AND_WORLD_POSE_"+
      ("PASS" if passed else "FAIL")+" "+json.dumps({
      "source_bytes":receipt["native_raw_bytes"],
      "total_contacts":total,"per_finger":summary,"checks":conditions}),flush=True)
sys.exit(0 if passed else 1)
