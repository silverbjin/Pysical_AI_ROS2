#!/usr/bin/env python3
"""Independent post-run Ch08 torque diagnostics: scope and raw metrics audit."""
import hashlib
import json
import math
from pathlib import Path
import sys

if len(sys.argv)!=5:
    raise SystemExit("usage: audit RECEIPT FROZEN_ZIP ORIGINAL_XML ORIGINAL_ENV")
receipt,zipfile,xml,envsrc=map(Path,sys.argv[1:])
r=json.loads(receipt.read_text(encoding="utf-8"))
assert r["chapter"]=="Ch08" and r["section"]=="8.7"
assert r["scope"]=="original_mujoco_real_torque_pd_vs_zero_input_test_only"
assert r["status"]=="SCOPED_PASS"
assert r["seed_values"]==[1000,1001,1002]
assert r["max_original_env_steps"]==300
assert r["simulated_max_time_s"]==3.0
assert r["prior_frozen_ppo_evaluation"]=="0_OF_10_SUCCESS_NOT_RERUN"
assert r["prior_geometric_ik"]=="10_OF_10_POSITION_IK_CANDIDATES_NOT_RERUN"
assert r["control_method"]=="test_only_joint_PD_plus_MuJoCo_bias_not_book_PPO"
assert r["kp"]==40 and r["kd"]==5
assert r["original_motor_action_range"]==[-1,1]
assert r["stored_ppo_zip_unchanged"] and r["torque_bounds_verified"] and r["asset_unchanged"]
assert r["ppo_inference"]==r["ppo_retraining"]==r["hardware"]==r["gui"]=="NOT_RUN"
assert r["stable_tracking"]=="NOT_PROVEN"
assert r["ch07_rgbd"]=="BLOCKED" and r["ch10"]=="HOLD"
for p in (zipfile,xml,envsrc):
    assert p.is_file()
    assert r["original_asset_sha256"][str(p.resolve())]==hashlib.sha256(p.read_bytes()).hexdigest()
rows=r["per_seed"]
assert len(rows)==3 and [x["seed"] for x in rows]==[1000,1001,1002]
approach=0;reaches=0
for row in rows:
    assert len(row["original_target_xyz_m"])==3
    assert 0<=row["ik_candidate_residual_m"]<0.05
    assert row["ik_initial_goal_distance_m"]>=0
    zero=row["zero_torque"]
    pd=row["bounded_pd"]
    assert zero["seed"]==pd["seed"]==row["seed"]
    assert zero["controller"]=="zero_torque_baseline"
    assert pd["controller"]=="test_only_joint_pd"
    assert math.isclose(zero["initial_distance_m"],pd["initial_distance_m"],abs_tol=1e-7)
    assert zero["mean_motor_magnitude"]==zero["max_motor_magnitude"]==0
    assert 0.001<pd["mean_motor_magnitude"]<=1.0
    assert 0<pd["max_motor_magnitude"]<=1.000001
    assert pd["joint_motion_norm_rad"]>=0.05
    for t in (zero,pd):
        assert 1<=t["steps"]<=300
        assert t["sim_duration_sec"]<=3.01
        assert len(t["final_joint_positions_rad"])==6
        assert all(math.isfinite(v) for v in t["final_joint_positions_rad"])
        for key in ("initial_distance_m","final_distance_m","minimum_distance_m","joint_motion_norm_rad"):
            assert math.isfinite(t[key]) and t[key]>=0
        assert abs(t["reduction_to_closest_m"]-(t["initial_distance_m"]-t["minimum_distance_m"]))<1e-8
        if t["actual_goal_reached"]:
            assert t["minimum_distance_m"]<0.05
    approach+=pd["reduction_to_closest_m"]>=0.10
    reaches+=bool(pd["actual_goal_reached"])
assert approach==r["at_least_0p10m_closer_count"] and approach>=1
assert reaches==r["actual_0p05m_success_count"]
assert r["zero_control_success_count"]==sum(x["zero_torque"]["actual_goal_reached"] for x in rows)
print("CH08_87_INDEPENDENT_REAL_FINITE_TORQUE_VS_ZERO_DYNAMICS_AUDIT_PASS "
      f"approached={approach}/3 reached={reaches}/3",flush=True)
