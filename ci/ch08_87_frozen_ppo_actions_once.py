#!/usr/bin/env python3
"""Ch08 §8.7: original frozen PPO action/reward diagnosis, NOT policy acceptance.

Measure deterministic action amplitudes, clipping, temporal changes, target
conditioning, reward components and true EE-target distances in just
3 * 120 original MuJoCo steps. The accepted 10 * 300 episode evaluation
and the test-only PD 3/3 dynamics tests are NOT rerun. No training or ZIP edit.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import torch
from stable_baselines3 import PPO

ROOT=Path(__file__).resolve().parents[1]
WS=ROOT/"Ch08/ros2_ws"
sys.path.insert(0,str(WS))
from rl_env import ReachEnv

OUT=ROOT/"ci-results/ch08-87-actions"
OUT.mkdir(parents=True,exist_ok=True)
MODEL=WS/"models/ppo_reach_final.zip"
XML=WS/"src/my_robot_description/assets/simple_arm_6dof.xml"
ENV_SRC=WS/"rl_env.py"
SEEDS=(1000,1001,1002)
TARGET_SEEDS=tuple(range(1000,1010))
HORIZON=120
SAT_BOUNDARY=0.98
NEAR_ZERO=0.02


def hash_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()


def finite_action(model,observation):
    raw,_=model.predict(observation,deterministic=True)
    arr=np.asarray(raw,dtype=np.float64)
    if arr.shape!=(6,) or not np.isfinite(arr).all():
        raise RuntimeError("CH08_87_FROZEN_PPO_NONFINITE_OR_WRONG_ACTION_SHAPE")
    if np.max(np.abs(arr))>1.000001:
        raise RuntimeError("CH08_87_FROZEN_PPO_MOTOR_ACTION_OUT_OF_BOUNDS")
    return arr


def offline_goal_conditioning(model):
    """Keep initial 6 joint pos/vel & EE fixed; vary only original sampled goals."""
    env=ReachEnv(render_mode=None)
    try:
        goals=[]
        base=None
        for seed in TARGET_SEEDS:
            ob,_=env.reset(seed=seed)
            if base is None:
                base=ob.copy()
            goals.append(np.asarray(ob[15:18],dtype=np.float64).copy())
        assert len(goals)==10 and all(np.isfinite(p).all() for p in goals)
        actions=[]
        for goal in goals:
            ob=base.copy()
            ob[15:18]=goal.astype(np.float32)
            actions.append(finite_action(model,ob))
        a=np.asarray(actions)
        assert a.shape==(10,6)
        spans=np.ptp(a,axis=0)
        max_pairwise=max(float(np.linalg.norm(u-v)) for u in a for v in a)
        record={
            "seeds":list(TARGET_SEEDS),
            "reference_state_seed":1000,
            "same_robot_state_all_cases":True,
            "vary_only_goal_xyz":True,
            "target_xyz_m":[p.tolist() for p in goals],
            "frozen_policy_actions":[p.tolist() for p in a],
            "per_motor_target_conditioned_span":spans.tolist(),
            "max_pairwise_action_delta_l2":max_pairwise,
        }
        print("CH08_87_FROZEN_PPO_FIXED_STATE_GOAL_SENSITIVITY_OBSERVED "
              f"max_pairwise_action_delta_l2={max_pairwise:.6f}",flush=True)
        return record
    finally:
        env.close()


def run_short_trace(model,seed):
    # Separate original environment each seed, no reset() behavior patches.
    env=ReachEnv(render_mode=None)
    try:
        ob,_=env.reset(seed=seed)
        assert ob.shape==(18,) and env.model.nu==6
        target=ob[15:18].astype(float).copy()
        initial=float(np.linalg.norm(ob[12:15]-ob[15:18]))
        trace=[]
        previous=None
        for step in range(HORIZON):
            action=finite_action(model,ob)
            ob,reward,terminated,truncated,info=env.step(action.astype(np.float32))
            if ob.shape!=(18,) or not np.isfinite(ob).all():
                raise RuntimeError("CH08_87_OBSERVATION_NONFINITE")
            distance=float(info.get("distance",float("nan")))
            independently=float(np.linalg.norm(ob[12:15]-ob[15:18]))
            if not math.isfinite(distance) or abs(distance-independently)>1e-4:
                raise RuntimeError("CH08_87_ORIGINAL_TRUE_DISTANCE_DISAGREEMENT")
            if not np.allclose(ob[15:18],target,atol=1e-5):
                raise RuntimeError("CH08_87_ORIGINAL_TARGET_MOVED")
            if not np.allclose(env.data.ctrl,action,atol=1e-6):
                raise RuntimeError("CH08_87_PPO_ACTION_NOT_APPLIED_TO_ACTUAL_MOTORS")
            components={k:float(info[k]) for k in (
                "reward_dist","reward_ctrl","reward_smooth",
                "reward_contact","reward_bonus")}
            if any(not math.isfinite(v) for v in components.values()):
                raise RuntimeError("CH08_87_REWARD_COMPONENT_NONFINITE")
            computed=sum(components.values())
            if abs(float(reward)-computed)>1e-5 or abs(float(info["reward_total"])-computed)>1e-5:
                raise RuntimeError("CH08_87_REWARD_COMPONENT_DECOMPOSITION_MISMATCH")
            delta=float(np.linalg.norm(action-previous)) if previous is not None else None
            sample={
                "step":step+1,
                "sim_time_sec":float(env.data.time),
                "actual_action":action.tolist(),
                "distance_m":distance,
                "reward_total":float(reward),
                "reward_components":components,
                "action_delta_l2":delta,
                "actual_joint_position_rad":np.asarray(env.data.qpos[:6],dtype=float).tolist(),
                "actual_joint_velocity_rad_s":np.asarray(env.data.qvel[:6],dtype=float).tolist(),
            }
            trace.append(sample)
            previous=action.copy()
            if terminated or truncated:
                break
        if not trace:
            raise RuntimeError("CH08_87_NO_FROZEN_PPO_ACTUAL_STEPS")
        a=np.array([t["actual_action"] for t in trace])
        distances=[t["distance_m"] for t in trace]
        means=a.mean(axis=0)
        stdev=a.std(axis=0)
        near_sat=np.mean(np.abs(a)>=SAT_BOUNDARY,axis=0)
        near_zero=np.mean(np.abs(a)<=NEAR_ZERO,axis=0)
        delta=[x["action_delta_l2"] for x in trace if x["action_delta_l2"] is not None]
        rewards={k:sum(t["reward_components"][k] for t in trace) for k in trace[0]["reward_components"]}
        summary={
            "seed":seed,
            "step_count":len(trace),
            "initial_distance_m":initial,
            "minimum_distance_m":min(distances),
            "final_distance_m":distances[-1],
            "closest_approach_m":initial-min(distances),
            "last_step_in_original_success_radius":distances[-1]<0.05,
            "mean_abs_action_per_motor":np.mean(np.abs(a),axis=0).tolist(),
            "mean_signed_action_per_motor":means.tolist(),
            "std_action_per_motor":stdev.tolist(),
            "fraction_at_or_above_0p98_per_motor":near_sat.tolist(),
            "fraction_below_0p02_per_motor":near_zero.tolist(),
            "overall_fraction_at_or_above_0p98":float(np.mean(np.abs(a)>=SAT_BOUNDARY)),
            "mean_action_delta_l2":float(np.mean(delta)) if delta else 0.0,
            "maximum_action_delta_l2":max(delta) if delta else 0.0,
            "actual_sim_time_sec":trace[-1]["sim_time_sec"],
            "summed_reward_components":rewards,
        }
        path=OUT/f"trace_seed_{seed}.json"
        with path.open("x",encoding="utf-8") as f:
            json.dump(trace,f,indent=2,sort_keys=True)
            f.write("\n")
        print(
            "CH08_87_ACTUAL_FROZEN_PPO_ACTION_TRACE "
            f"seed={seed} steps={len(trace)} "
            f"init_m={initial:.5f} final_m={summary['final_distance_m']:.5f} "
            f"sat_frac={summary['overall_fraction_at_or_above_0p98']:.4f} "
            f"mean_delta={summary['mean_action_delta_l2']:.5f}",
            flush=True,
        )
        return summary
    finally:
        env.close()


def main():
    for p in (MODEL,XML,ENV_SRC):
        if not p.is_file():
            raise FileNotFoundError(f"CH08_87_REQUIRED_FROZEN_ASSET_MISSING {p}")
    original_hashes={str(p.relative_to(ROOT)):hash_file(p) for p in (MODEL,XML,ENV_SRC)}
    torch.set_num_threads(2)
    model=PPO.load(str(MODEL),device="cpu")
    if tuple(model.observation_space.shape)!=(18,) or tuple(model.action_space.shape)!=(6,):
        raise RuntimeError("CH08_87_FROZEN_PPO_SPACE_CONTRACT_CHANGED")
    conditioning=offline_goal_conditioning(model)
    rows=[run_short_trace(model,seed) for seed in SEEDS]
    result={
        "chapter":"Ch08","section":"8.7","status":"SCOPED_PASS",
        "scope":"frozen_PPO_short_action_reward_and_target_conditioning_diagnostic",
        "source_sha":os.environ.get("RUN_SOURCE_SHA","LOCAL_UNPINNED"),
        "original_assets_sha256":original_hashes,
        "original_assets_unchanged":all(
            hash_file(ROOT/path)==digest for path,digest in original_hashes.items()
        ),
        "seeds":list(SEEDS),
        "observations_per_seed_at_most":HORIZON,
        "original_300_step_x_10_policy_evaluation":"NOT_RERUN",
        "prior_policy_success_result":"0_OF_10_PERFORMANCE_FAIL_PRESERVED",
        "prior_PD_3_seed_success":"3_OF_3_TEST_ONLY_NOT_RERUN",
        "deterministic_frozen_PPO_loaded":True,
        "policy_training":"NOT_RUN",
        "goal_conditioned_fixed_state_probe":conditioning,
        "action_saturation_threshold":SAT_BOUNDARY,
        "action_near_zero_threshold":NEAR_ZERO,
        "per_seed":rows,
        "total_original_env_steps":sum(x["step_count"] for x in rows),
        "control_mode":"ACTUAL_FROZEN_PPO_ACTIONS_IN_ORIGINAL_MUJOCO",
        "policy_performance_acceptance":"NOT_ACCEPTED_FROM_SHORT_DIAGNOSTIC",
        "real_hardware":"NOT_RUN","gui":"NOT_RUN",
        "ch07_rgbd":"BLOCKED","ch10":"HOLD",
    }
    if not result["original_assets_unchanged"]:
        raise RuntimeError("CH08_87_FROZEN_ASSETS_MODIFIED")
    path=OUT/"receipt.json"
    with path.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n");f.flush();os.fsync(f.fileno())
    print("CH08_87_REAL_FROZEN_PPO_ACTION_AND_REWARD_DIAGNOSTIC_SCOPED_PASS "
          f"steps={result['total_original_env_steps']}",flush=True)
    print("CH08_87_ORIGINAL_PPO_0_OF_10_FAILURE_UNCHANGED_NO_RETRAIN_PASS",flush=True)


if __name__=="__main__":
    main()
