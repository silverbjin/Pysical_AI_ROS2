#!/usr/bin/env python3
"""Independent post-run receipt auditor; never redo original IK cases."""
import hashlib
import json
import math
from pathlib import Path
import sys

assert len(sys.argv)==3
receipt=Path(sys.argv[1])
source=Path(sys.argv[2])
r=json.loads(receipt.read_text(encoding="utf-8"))
assert r["chapter"]=="Ch06" and r["section"]=="6.7"
assert r["status"]=="SCOPED_PASS"
assert r["scenario"]=="original_2d_ik_failure_and_bounded_test_only_dls"
assert r["original_source_unchanged"] is True
assert r["original_source_sha256"]==hashlib.sha256(source.read_bytes()).hexdigest()
s=r["original_singularity"]
assert s["status"]=="Divergence (Singularity!)" and s["history_points"]==1
assert abs(s["det_jacobian"])<1e-12 and s["min_singular_value"]<1e-12
e=r["original_explosion"]
assert e["status"]=="Divergence (Explosion!)" and e["history_points"]==2
assert e["angle_jump_norm_rad"]>2.5 and math.isfinite(e["angle_jump_norm_rad"])
d=r["test_only_dls"]
assert d["status"]=="CONVERGED" and 0<d["final_error_m"]<=.001
assert 0<d["max_step_rad"]<=.150000000001 and 0<d["steps"]<=400
assert len(d["final_angles"])==2
assert all(math.isfinite(x) for x in d["final_angles"])
assert len(r["two_elbow_solutions_fk_error_m"])==2
assert max(r["two_elbow_solutions_fk_error_m"])<1e-12
assert r["unreachable_status"]=="UNREACHABLE_REJECTED"
limits=r["book_original_xacro_joint_limits"]
assert len(limits)==5 and set(limits)=={
 "joint1","joint2","joint3","joint4","joint_wrist"}
assert all(x["lower"]<x["upper"] and x["velocity"]>0 for x in limits.values())
assert r["original_gui_slider_and_rollback"]==r["collision_planning_scene"]==r["ik_solver_ros_integration"]==r["physical_robot"]=="NOT_RUN"
assert r["ch06_64_65_66_retest"]=="NOT_RUN"
assert r["ch07_rgbd"]=="BLOCKED" and r["ch10"]=="HOLD"
print("CH06_67_INDEPENDENT_BOOK_SOURCE_HASH_FAILURE_AND_DLS_RECEIPT_PASS",flush=True)
