#!/usr/bin/env python3
"""Independent audit of original PPO short actual MuJoCo trace receipts.

Uses only raw stored step traces + original asset SHA256; no model load,
PPO replay, train, synthetic rewards or extra MuJoCo simulation.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np

if len(sys.argv)!=5:
    raise SystemExit("usage: audit RECEIPT ORIGINAL_ZIP ORIGINAL_XML ORIGINAL_ENV")
receipt,zipfile,xml,envfile=map(Path,sys.argv[1:])
r=json.loads(receipt.read_text(encoding="utf-8"))
assert r["chapter"]=="Ch08" and r["section"]=="8.7"
assert r["status"]=="SCOPED_PASS"
assert r["scope"]=="frozen_PPO_short_action_reward_and_target_conditioning_diagnostic"
assert r["original_assets_unchanged"] and r["deterministic_frozen_PPO_loaded"]
assert r["seeds"]==[1000,1001,1002]
assert r["observations_per_seed_at_most"]==120
assert r["original_300_step_x_10_policy_evaluation"]=="NOT_RERUN"
assert r["prior_policy_success_result"]=="0_OF_10_PERFORMANCE_FAIL_PRESERVED"
assert r["prior_PD_3_seed_success"]=="3_OF_3_TEST_ONLY_NOT_RERUN"
assert r["policy_training"]=="NOT_RUN"
assert r["policy_performance_acceptance"]=="NOT_ACCEPTED_FROM_SHORT_DIAGNOSTIC"
assert r["real_hardware"]==r["gui"]=="NOT_RUN"
assert r["ch07_rgbd"]=="BLOCKED" and r["ch10"]=="HOLD"
assert r["action_saturation_threshold"]==.98
assert r["action_near_zero_threshold"]==.02

ROOT=Path(__file__).resolve().parents[1]
for p in (zipfile,xml,envfile):
    assert p.is_file()
    relative=str(p.resolve().relative_to(ROOT))
    assert r["original_assets_sha256"][relative]==hashlib.sha256(p.read_bytes()).hexdigest()

sens=r["goal_conditioned_fixed_state_probe"]
assert sens["seeds"]==list(range(1000,1010))
assert sens["reference_state_seed"]==1000
assert sens["same_robot_state_all_cases"] and sens["vary_only_goal_xyz"]
goals=np.array(sens["target_xyz_m"],dtype=np.float64)
actions=np.array(sens["frozen_policy_actions"],dtype=np.float64)
assert goals.shape==(10,3) and actions.shape==(10,6)
assert np.isfinite(goals).all() and np.isfinite(actions).all()
assert (np.abs(actions)<=1.000001).all()
assert len(set(tuple(g) for g in goals))==10
spans=np.ptp(actions,axis=0)
assert np.allclose(spans,sens["per_motor_target_conditioned_span"],atol=1e-9)
maxpair=max(np.linalg.norm(u-v) for u in actions for v in actions)
assert math.isclose(maxpair,sens["max_pairwise_action_delta_l2"],abs_tol=1e-9)

assert [row["seed"] for row in r["per_seed"]]==[1000,1001,1002]
summed=0
for row in r["per_seed"]:
    seed=row["seed"]
    file=receipt.parent/f"trace_seed_{seed}.json"
    traces=json.loads(file.read_text(encoding="utf-8"))
    assert 1<=len(traces)<=120 and row["step_count"]==len(traces)
    assert [t["step"] for t in traces]==list(range(1,len(traces)+1))
    assert all(
        t["sim_time_sec"]>0 and len(t["actual_joint_position_rad"])==6
        and len(t["actual_joint_velocity_rad_s"])==6
        and all(math.isfinite(x) for x in t["actual_joint_position_rad"])
        and all(math.isfinite(x) for x in t["actual_joint_velocity_rad_s"])
        for t in traces
    )
    sim=[t["sim_time_sec"] for t in traces]
    assert all(b>a for a,b in zip(sim,sim[1:]))
    acts=np.array([t["actual_action"] for t in traces],dtype=float)
    assert acts.shape==(len(traces),6)
    assert np.isfinite(acts).all() and (np.abs(acts)<=1.000001).all()
    dist=[t["distance_m"] for t in traces]
    assert all(math.isfinite(d) and d>=0 for d in dist)
    assert math.isclose(row["minimum_distance_m"],min(dist),abs_tol=1e-9)
    assert math.isclose(row["final_distance_m"],dist[-1],abs_tol=1e-9)
    assert math.isclose(row["closest_approach_m"],row["initial_distance_m"]-min(dist),abs_tol=1e-9)
    assert row["last_step_in_original_success_radius"]==(dist[-1]<.05)
    for item in traces:
        comps=item["reward_components"]
        assert set(comps)=={
           "reward_dist","reward_ctrl","reward_smooth","reward_contact","reward_bonus"
        }
        assert all(math.isfinite(x) for x in comps.values())
        assert math.isclose(sum(comps.values()),item["reward_total"],abs_tol=1e-5)
    for key in traces[0]["reward_components"]:
        actual=sum(t["reward_components"][key] for t in traces)
        assert math.isclose(actual,row["summed_reward_components"][key],abs_tol=1e-6)
    for key,actual in (
        ("mean_abs_action_per_motor",np.abs(acts).mean(axis=0)),
        ("mean_signed_action_per_motor",acts.mean(axis=0)),
        ("std_action_per_motor",acts.std(axis=0)),
        ("fraction_at_or_above_0p98_per_motor",(np.abs(acts)>=.98).mean(axis=0)),
        ("fraction_below_0p02_per_motor",(np.abs(acts)<=.02).mean(axis=0)),
    ):
        assert np.allclose(actual,row[key],atol=1e-9),key
    assert math.isclose(
        row["overall_fraction_at_or_above_0p98"],
        float((np.abs(acts)>=.98).mean()),abs_tol=1e-9
    )
    deltas=np.linalg.norm(np.diff(acts,axis=0),axis=1)
    assert traces[0]["action_delta_l2"] is None
    for t,v in zip(traces[1:],deltas):
        assert math.isclose(v,t["action_delta_l2"],abs_tol=1e-9)
    assert math.isclose(
        float(np.mean(deltas)) if len(deltas) else 0.0,
        row["mean_action_delta_l2"],abs_tol=1e-9)
    assert math.isclose(
        float(np.max(deltas)) if len(deltas) else 0.0,
        row["maximum_action_delta_l2"],abs_tol=1e-9)
    assert math.isclose(row["actual_sim_time_sec"],sim[-1],abs_tol=1e-9)
    summed+=len(traces)
assert r["total_original_env_steps"]==summed
print("CH08_87_INDEPENDENT_FROZEN_PPO_ACTION_AND_REWARD_RECEIPT_PASS "
      f"steps={summed} max_goal_conditioned_action_delta={maxpair:.6f}",flush=True)
