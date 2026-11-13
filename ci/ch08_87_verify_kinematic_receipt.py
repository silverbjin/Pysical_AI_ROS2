#!/usr/bin/env python3
"""Independent receipt audit: only mathematical model-goal reachability."""
import hashlib
import json
import math
from pathlib import Path
import sys

if len(sys.argv)!=5:
    raise SystemExit("usage: verify_receipt.py RECEIPT ZIP XML ORIGINAL_RL_ENV")
receipt,archive,xml,src=map(Path,sys.argv[1:])
x=json.loads(receipt.read_text())
assert x["chapter"]=="Ch08" and x["section"]=="8.7"
assert x["scope"]=="original_seeded_target_kinematic_feasibility_diagnostic_only"
assert x["status"]=="SCOPED_PASS"
for file,key in [(archive,"original_zip_sha256"),(xml,"original_xml_sha256"),(src,"original_environment_sha256")]:
    assert file.is_file() and x[key]==hashlib.sha256(file.read_bytes()).hexdigest()
assert x["seed_start"]==1000 and x["seed_count"]==10
assert x["baseline_existing_policy_run"]=="43361732383"
assert x["baseline_policy_result"]=="0_OF_10_REACH_SUCCESSES_NOT_RERUN"
assert x["goal_success_radius_m"]==0.05
assert x["model_nq"]==x["model_nv"]==x["model_nu"]==6
assert x["max_allowed_update_norm_rad"]==0.2
assert x["iterations_per_restart"]==175 and x["restarts_per_goal"]==8
rows=x["all_target_rows"]
assert len(rows)==10 and [y["seed"] for y in rows]==list(range(1000,1010))
count=sum(y["kinematic_found"] for y in rows)
assert x["kinematic_found_count"]==count and count>=1
assert x["kinematic_not_found_count"]==10-count
for y in rows:
    assert len(y["sampled_target_xyz_m"])==3 and len(y["initial_ee_xyz_m"])==3
    assert math.isclose(
      math.dist(y["sampled_target_xyz_m"],y["initial_ee_xyz_m"]),
      y["initial_distance_m"],rel_tol=0,abs_tol=1e-6
    )
    assert math.dist(y["sampled_target_xyz_m"],[0,0,0])<0.5001
    assert y["restart_count"]==8
    assert all(math.isfinite(float(y[k])) and float(y[k])>=0 for k in
       ("initial_distance_m","best_kinematic_residual_m","maximum_update_norm_rad"))
    assert y["maximum_update_norm_rad"]<=0.200000001
    assert 0<=y["best_attempt_iterations"]<=175
    if y["kinematic_found"]:
        assert y["best_kinematic_residual_m"]<0.05
        assert len(y["best_joint_solution_rad"])==6
        assert all(math.isfinite(v) for v in y["best_joint_solution_rad"])
    else:
        assert y["best_joint_solution_rad"] is None
assert len(x["original_joint_range_rad"])==len(x["original_joint_limited"])==6
assert x["frozen_ppo_evaluation"]=="NOT_RERUN"
assert x["ppo_retraining"]==x["collisions_and_constraints"]==x["controller_safety"]==x["hardware"]=="NOT_RUN"
assert x["dynamical_reachability"]=="NOT_PROVEN"
assert x["ch07_rgbd"]=="BLOCKED" and x["ch10"]=="HOLD"
print(f"CH08_87_INDEPENDENT_GEOMETRIC_TARGET_REACHABILITY_RECEIPT_PASS found={count}/10",flush=True)
