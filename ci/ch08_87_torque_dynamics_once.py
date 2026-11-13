#!/usr/bin/env python3
"""Ch08 §8.7 actual MuJoCo torque-dynamics boundary, NOT a PPO retest.

For fixed goals 1000–1002, use original ReachEnv.step(action) and a *test-only*
joint PD+gravity controller, targeting a position-only IK candidate. Compare
with unchanged zero torque on the same seed. 300 steps = 3 simulated seconds.
Never claim that the stored PPO, optimal trajectory, or real hardware passed.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
WS=ROOT/"Ch08/ros2_ws"
sys.path.insert(0,str(WS))
sys.path.insert(0,str(ROOT/"ci"))
from rl_env import ReachEnv
from ch08_87_kinematic_diagnosis import solve_position_ik

OUT=ROOT/"ci-results/ch08-87-dynamics"
OUT.mkdir(parents=True,exist_ok=True)
ASSETS=[
    WS/"models/ppo_reach_final.zip",
    WS/"src/my_robot_description/assets/simple_arm_6dof.xml",
    WS/"rl_env.py",
]
SEEDS=(1000,1001,1002)
LIMIT=300
KP=40.0
KD=5.0
RADIUS=0.05


def checksum(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def reset_original(env,seed):
    # The book's env.reset() sets qpos/qvel but does not zero MuJoCo time
    # or all integration/actuation state. Explicitly isolate the two trials
    # in this diagnostic to compare identical seeded initial states.
    mujoco.mj_resetData(env.model,env.data)
    observation,_=env.reset(seed=seed)
    assert observation.shape==(18,)
    assert env.model.nu==env.model.nv==env.model.nq==6
    q=np.array(env.data.qpos[:6],dtype=float)
    target=np.array(observation[15:18],dtype=float)
    initial=float(np.linalg.norm(observation[12:15]-target))
    return q,target,initial


def find_position_candidate(env,seed):
    q0,target,dist=reset_original(env,seed)
    m=env.model
    site=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_SITE,"ee_site")
    assert site>=0
    rng=np.random.default_rng(86701+seed)
    starts=[
        q0.copy(),np.zeros(6),
        np.array([0.0,0.7,-1.4,0.0,0.7,0.0]),
        np.array([0.0,-0.7,1.4,0.0,-0.7,0.0]),
    ]
    starts.extend(rng.uniform(-1.2,1.2,size=(4,6)))
    results=[]
    for start in starts:
        results.append(solve_position_ik(m,env.data,site,target,start))
    # Restore exactly the original seeded MuJoCo task before any torque step.
    qr,target_after,dist_after=reset_original(env,seed)
    assert np.array_equal(qr,q0) and np.array_equal(target_after,target)
    assert abs(dist_after-dist)<1e-9
    feasible=[r for r in results if r["converged"]]
    if not feasible:
        raise RuntimeError(f"CH08_87_DYNAMIC_GOAL_NO_IK_CANDIDATE seed={seed}")
    # Prefer a close solution, but require the original residual below 5 cm.
    chosen=min(feasible,key=lambda x:float(np.linalg.norm(
        np.asarray(x["joint_solution_rad"])-q0)))
    goal=np.asarray(chosen["joint_solution_rad"],dtype=float)
    assert goal.shape==(6,) and np.isfinite(goal).all()
    return goal,target,dist,chosen


def run_original_physics(env,seed,policy,goal=None):
    q0,target,initial=reset_original(env,seed)
    model=env.model
    gears=np.asarray(model.actuator_gear[:,0],dtype=float)
    assert gears.shape==(6,) and np.all(gears>0)
    assert np.all(model.actuator_ctrllimited[:6])
    ctrlrange=np.asarray(model.actuator_ctrlrange[:6],dtype=float)
    assert np.allclose(ctrlrange[:,0],-1.0) and np.allclose(ctrlrange[:,1],1.0)
    if policy=="test_only_joint_pd":
        assert goal is not None and goal.shape==(6,)
    else:
        assert policy=="zero_torque_baseline"
    distances=[]
    physical_times=[]
    controls=[]
    joint_motion=[]
    contact_max=0
    reached=False
    for i in range(LIMIT):
        if policy=="test_only_joint_pd":
            # qfrc_bias is genuine model gravity and Coriolis compensation.
            # All commands are scaled to original motor gear / ctrlrange.
            torque=(KP*(goal-env.data.qpos[:6])
                    -KD*env.data.qvel[:6]
                    +env.data.qfrc_bias[:6])
            command=np.clip(torque/gears,ctrlrange[:,0],ctrlrange[:,1])
        else:
            command=np.zeros(6,dtype=float)
        if not np.isfinite(command).all():
            raise RuntimeError("CH08_87_NONFINITE_FINITE_TORQUE_COMMAND")
        ob,reward,terminated,truncated,info=env.step(command.astype(np.float32))
        actual_distance=float(info["distance"])
        check_distance=float(np.linalg.norm(ob[12:15]-ob[15:18]))
        if not (math.isfinite(actual_distance) and math.isfinite(float(reward))
                and abs(actual_distance-check_distance)<1e-4
                and np.isfinite(ob).all()):
            raise RuntimeError("CH08_87_BAD_ACTUAL_MUJOCO_STEP_AND_GEOMETRY")
        if np.max(np.abs(command))>1.000001:
            raise RuntimeError("CH08_87_ORIGINAL_MOTOR_LIMIT_EXCEEDED")
        distances.append(actual_distance)
        physical_times.append(float(env.data.time))
        controls.append(command.copy())
        joint_motion.append(np.array(env.data.qpos[:6],dtype=float))
        contact_max=max(contact_max,int(env.data.ncon))
        if terminated or truncated:
            reached=bool(info.get("is_success")) and actual_distance<RADIUS
            break
    assert distances and np.isfinite(distances).all()
    trace={
        "seed":seed,"controller":policy,
        "initial_distance_m":initial,
        "final_distance_m":distances[-1],
        "minimum_distance_m":min(distances),
        "reduction_to_closest_m":initial-min(distances),
        "actual_goal_reached":reached,
        "steps":len(distances),
        "sim_duration_sec":physical_times[-1],
        "mean_motor_magnitude":float(np.mean(np.abs(controls))),
        "max_motor_magnitude":float(np.max(np.abs(controls))),
        "joint_motion_norm_rad":float(np.linalg.norm(joint_motion[-1]-q0)),
        "max_contacts":contact_max,
        "final_joint_positions_rad":joint_motion[-1].tolist(),
    }
    return trace


def main():
    before={str(p):checksum(p) for p in ASSETS}
    test_rows=[]
    for seed in SEEDS:
        env=ReachEnv(render_mode=None)
        try:
            candidate,target,initial,ik=find_position_candidate(env,seed)
            base=run_original_physics(env,seed,"zero_torque_baseline")
            controlled=run_original_physics(env,seed,"test_only_joint_pd",candidate)
            assert abs(base["initial_distance_m"]-initial)<1e-7
            assert abs(controlled["initial_distance_m"]-initial)<1e-7
            assert base["mean_motor_magnitude"]==base["max_motor_magnitude"]==0.0
            assert controlled["max_motor_magnitude"]<=1.000001
            assert controlled["mean_motor_magnitude"]>0.001
            if controlled["joint_motion_norm_rad"]<0.05:
                raise RuntimeError(
                    f"CH08_87_TORQUE_ISSUED_BUT_NO_REAL_JOINT_MOTION seed={seed}"
                )
            test_rows.append({
                "seed":seed,"original_target_xyz_m":target.tolist(),
                "ik_initial_goal_distance_m":initial,
                "ik_candidate_residual_m":ik["final_error_m"],
                "zero_torque":base,
                "bounded_pd":controlled,
            })
            print(
                "CH08_87_REAL_TORQUE_DYNAMICS_DIAGNOSTIC "
                f"seed={seed} init_m={initial:.5f} "
                f"zero_best_m={base['minimum_distance_m']:.5f} "
                f"pd_best_m={controlled['minimum_distance_m']:.5f} "
                f"pd_final_m={controlled['final_distance_m']:.5f} "
                f"pd_goal_reached={int(controlled['actual_goal_reached'])} "
                f"pd_max_ctrl={controlled['max_motor_magnitude']:.5f}",
                flush=True,
            )
        finally:
            env.close()
    approached=sum(x["bounded_pd"]["reduction_to_closest_m"]>=0.10 for x in test_rows)
    within=sum(bool(x["bounded_pd"]["actual_goal_reached"]) for x in test_rows)
    baseline_within=sum(bool(x["zero_torque"]["actual_goal_reached"]) for x in test_rows)
    data={
        "chapter":"Ch08","section":"8.7","status":"SCOPED_PASS" if approached>=1 else "FAIL_NO_MEASURABLE_CONTROLLED_APPROACH",
        "scope":"original_mujoco_real_torque_pd_vs_zero_input_test_only",
        "source_sha":os.environ.get("RUN_SOURCE_SHA","LOCAL_UNPINNED"),
        "prior_frozen_ppo_evaluation":"0_OF_10_SUCCESS_NOT_RERUN",
        "prior_geometric_ik":"10_OF_10_POSITION_IK_CANDIDATES_NOT_RERUN",
        "seed_values":list(SEEDS),"max_original_env_steps":LIMIT,
        "simulated_max_time_s":LIMIT*5*0.002,
        "control_method":"test_only_joint_PD_plus_MuJoCo_bias_not_book_PPO",
        "kp":KP,"kd":KD,
        "original_motor_action_range":[-1.0,1.0],
        "per_seed":test_rows,
        "at_least_0p10m_closer_count":approached,
        "actual_0p05m_success_count":within,
        "zero_control_success_count":baseline_within,
        "original_asset_sha256":before,
        "asset_unchanged":all(checksum(p)==before[str(p)] for p in ASSETS),
        "stored_ppo_zip_unchanged":True,
        "torque_bounds_verified":True,
        "dynamical_controller_claim":"TEST_ONLY_NOT_SAFE_OR_OPTIMAL",
        "ppo_retraining":"NOT_RUN",
        "ppo_inference":"NOT_RUN",
        "stable_tracking":"NOT_PROVEN",
        "hardware":"NOT_RUN","gui":"NOT_RUN",
        "ch07_rgbd":"BLOCKED","ch10":"HOLD",
    }
    out=OUT/"receipt.json"
    with out.open("x",encoding="utf-8") as f:
        json.dump(data,f,indent=2,sort_keys=True,ensure_ascii=False)
        f.write("\n");f.flush();os.fsync(f.fileno())
    if not data["asset_unchanged"]:
        raise RuntimeError("CH08_87_ORIGINAL_ASSETS_WERE_MODIFIED")
    if approached<1:
        raise RuntimeError("CH08_87_TORQUE_FEEDBACK_NO_0P10M_APPROACH")
    print(
        "CH08_87_REAL_MUJOCO_FINITE_TORQUE_DYNAMICS_SCOPED_PASS "
        f"approached={approached}/{len(SEEDS)} within_5cm={within}/{len(SEEDS)} "
        f"zero_control_success={baseline_within}/{len(SEEDS)}",
        flush=True,
    )
    print("CH08_87_PRIOR_PPO_0_OF_10_UNCHANGED_AND_FROZEN_ASSETS_PASS",flush=True)


if __name__=="__main__":
    main()
