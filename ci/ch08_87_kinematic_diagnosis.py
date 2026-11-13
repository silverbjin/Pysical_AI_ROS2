#!/usr/bin/env python3
"""Ch08 §8.7: test-only geometric reachability of the frozen PPO task.

Reuses original ReachEnv and XML, samples original target seeds 1000..1009.
Searches MuJoCo SITE Jacobian IK with bounded damped least-squares,
WITHOUT env.step(), torque commands, policy evaluation, or retraining.
A converged kinematic candidate is not a dynamically safe control policy.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

import gymnasium
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
WS=ROOT/"Ch08/ros2_ws"
sys.path.insert(0,str(WS))
from rl_env import ReachEnv

OUT=ROOT/"ci-results/ch08-87-geometry"
OUT.mkdir(parents=True,exist_ok=True)
MODEL_ZIP=WS/"models/ppo_reach_final.zip"
MODEL_XML=WS/"src/my_robot_description/assets/simple_arm_6dof.xml"
SEEDS=list(range(1000,1010))
GOAL_RADIUS_M=0.05
DAMPING=0.08
MAX_UPDATE_RAD=0.20
ITERATIONS=175
RNG=np.random.default_rng(86701)


def sha256(file):
    h=hashlib.sha256()
    with file.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def solve_position_ik(model,data,site_id,target,initial):
    """Multi-iteration kinematic position IK, collision/actuation NOT checked."""
    q=np.asarray(initial,dtype=np.float64).copy()
    assert len(q)==model.nq==model.nv==6
    jacp=np.zeros((3,model.nv),dtype=np.float64)
    jacr=np.zeros((3,model.nv),dtype=np.float64)
    upper=np.where(model.jnt_limited[:6],model.jnt_range[:6,1],np.inf)
    lower=np.where(model.jnt_limited[:6],model.jnt_range[:6,0],-np.inf)
    best=float("inf")
    max_step=0.
    for i in range(ITERATIONS):
        data.qpos[:6]=q
        data.qvel[:6]=0.0
        mujoco.mj_forward(model,data)
        xyz=np.array(data.site_xpos[site_id],dtype=float)
        err=target-xyz
        dist=float(np.linalg.norm(err))
        if not math.isfinite(dist):
            raise RuntimeError("CH08_87_NONFINITE_KINEMATICS")
        best=min(best,dist)
        if dist<GOAL_RADIUS_M:
            return {"converged":True,"iterations":i,"final_error_m":dist,
                    "max_update_rad":max_step,"joint_solution_rad":q.tolist()}
        mujoco.mj_jacSite(model,data,jacp,jacr,site_id)
        update=jacp.T@np.linalg.solve(jacp@jacp.T+(DAMPING**2)*np.eye(3),err)
        assert np.isfinite(update).all(),"CH08_87_NONFINITE_JACOBIAN"
        norm=float(np.linalg.norm(update))
        if norm>MAX_UPDATE_RAD:
            update*=MAX_UPDATE_RAD/norm
            norm=MAX_UPDATE_RAD
        q=np.clip(q+update,lower,upper)
        max_step=max(max_step,norm)
    return {"converged":False,"iterations":ITERATIONS,
            "final_error_m":best,
            "max_update_rad":max_step,"joint_solution_rad":None}


def main():
    if not MODEL_ZIP.is_file() or not MODEL_XML.is_file():
        raise FileNotFoundError("CH08_87_FROZEN_ASSET_MISSING")
    zip_hash_before=sha256(MODEL_ZIP)
    xml_hash_before=sha256(MODEL_XML)
    original_source=WS/"rl_env.py"
    source_hash_before=sha256(original_source)
    env=ReachEnv(render_mode=None)
    rows=[]
    try:
        m=env.model
        assert (m.nq,m.nv,m.nu)==(6,6,6), "CH08_87_ROBOT_DOF_CHANGED"
        site_id=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_SITE,"ee_site")
        assert site_id>=0
        jrange=m.jnt_range[:6].tolist()
        jlimited=[bool(x) for x in m.jnt_limited[:6]]
        print("CH08_87_ORIGINAL_MUJOCO_MODEL_6DOF_AND_FROZEN_ZIP_PASS",flush=True)
        for seed in SEEDS:
            obs,reset_info=env.reset(seed=seed)
            assert obs.shape==(18,)
            target=np.array(obs[15:18],dtype=float)
            ee=np.array(obs[12:15],dtype=float)
            initial_distance=float(np.linalg.norm(target-ee))
            assert np.isfinite(target).all() and np.isfinite(ee).all()
            assert np.linalg.norm(target)<0.5001
            assert math.isfinite(initial_distance)
            original_q=np.array(env.data.qpos[:6],dtype=float)
            original_v=np.array(env.data.qvel[:6],dtype=float)
            # Deterministic restart schedule; NEVER use the PPO ZIP or env.step.
            starts=[
                original_q.copy(),
                np.zeros(6),
                np.array([0.,0.7,-1.4,0.,0.7,0.]),
                np.array([0.,-0.7,1.4,0.,-0.7,0.]),
            ]
            starts.extend(RNG.uniform(-1.2,1.2,size=(4,6)))
            options=[]
            try:
                for starting in starts:
                    options.append(solve_position_ik(m,env.data,site_id,target,starting))
            finally:
                env.data.qpos[:6]=original_q
                env.data.qvel[:6]=original_v
                mujoco.mj_forward(m,env.data)
            winner=min(options,key=lambda a:a["final_error_m"])
            # Save independently observed geometric goal, not a rewritten target.
            rows.append({
                "seed":seed,"sampled_target_xyz_m":target.tolist(),
                "initial_ee_xyz_m":ee.tolist(),
                "initial_distance_m":initial_distance,
                "kinematic_found":bool(any(a["converged"] for a in options)),
                "best_kinematic_residual_m":winner["final_error_m"],
                "best_attempt_iterations":winner["iterations"],
                "maximum_update_norm_rad":max(x["max_update_rad"] for x in options),
                "restart_count":len(starts),
                "best_joint_solution_rad":winner["joint_solution_rad"],
            })
            print("CH08_87_KINEMATIC_TARGET_DIAGNOSTIC "
                  f"seed={seed} initial_m={initial_distance:.5f} "
                  f"best_m={winner['final_error_m']:.5f} "
                  f"found={int(rows[-1]['kinematic_found'])}",flush=True)
        nfound=sum(x["kinematic_found"] for x in rows)
        if nfound==0:
            # Never infer 'all goals unreachable' from a failed local optimizer.
            raise RuntimeError("CH08_87_KINEMATIC_SOLVER_DID_NOT_VALIDATE_ANY_GOAL")
        result={
           "chapter":"Ch08","section":"8.7",
           "status":"SCOPED_PASS",
           "scope":"original_seeded_target_kinematic_feasibility_diagnostic_only",
           "source_sha":os.environ.get("RUN_SOURCE_SHA","UNPINNED"),
           "baseline_existing_policy_run":"43361732383",
           "baseline_policy_result":"0_OF_10_REACH_SUCCESSES_NOT_RERUN",
           "seed_start":1000,"seed_count":len(SEEDS),
           "goal_success_radius_m":GOAL_RADIUS_M,
           "kinematic_found_count":nfound,
           "kinematic_not_found_count":len(SEEDS)-nfound,
           "kinematic_solver_damping":DAMPING,
           "max_allowed_update_norm_rad":MAX_UPDATE_RAD,
           "iterations_per_restart":ITERATIONS,
           "restarts_per_goal":len(starts),
           "all_target_rows":rows,
           "model_nq":m.nq,"model_nv":m.nv,"model_nu":m.nu,
           "original_joint_limited":jlimited,
           "original_joint_range_rad":jrange,
           "original_zip_sha256":zip_hash_before,
           "original_xml_sha256":xml_hash_before,
           "original_environment_sha256":source_hash_before,
           "frozen_ppo_evaluation":"NOT_RERUN",
           "ppo_retraining":"NOT_RUN",
           "dynamical_reachability":"NOT_PROVEN",
           "collisions_and_constraints":"NOT_RUN",
           "controller_safety":"NOT_RUN",
           "hardware":"NOT_RUN",
           "ch07_rgbd":"BLOCKED","ch10":"HOLD",
        }
        target=OUT/"receipt.json"
        if target.exists():
            raise FileExistsError("CH08_87_REFUSE_OVERWRITE_ORIGINAL_EVIDENCE")
        with target.open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2,sort_keys=True,ensure_ascii=False)
            f.write("\n");f.flush();os.fsync(f.fileno())
        print("CH08_87_TRUE_MUJOCO_TARGET_KINEMATICS_SCOPED_PASS "
              f"found={nfound}/{len(rows)} previous_ppo_successes=0/10",flush=True)
    finally:
        env.close()
    assert sha256(MODEL_ZIP)==zip_hash_before
    assert sha256(MODEL_XML)==xml_hash_before
    assert sha256(original_source)==source_hash_before
    print("CH08_87_FROZEN_POLICY_XML_ENV_UNCHANGED_PASS",flush=True)


if __name__=="__main__":
    main()
