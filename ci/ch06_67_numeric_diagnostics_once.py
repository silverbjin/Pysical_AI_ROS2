#!/usr/bin/env python3
"""Ch06 §6.7 scoped numeric regression on the BOOK's own Planar2DOF class.

Load ONLY the class AST to avoid opening its Matplotlib GUI. The original
algorithm is intentionally singularity-prone; do not hide the failure.
The DLS comparison is a separate, bounded *teaching* alternative, NOT the
book's original solver and NOT approved for a physical ROS robot.
"""
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"Ch06/4_divergence.py"
URDF=ROOT/"Ch06/ros2_ws/src/my_robot_description/urdf/my_robot.urdf.xacro"
OUT=ROOT/"ci-results/ch06-67"
OUT.mkdir(parents=True,exist_ok=True)


def require(cond, message):
    if not cond:
        raise AssertionError(message)


def original_book_class():
    source=SOURCE.read_text(encoding="utf-8")
    tree=ast.parse(source,filename=str(SOURCE))
    classes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Planar2DOF"]
    require(len(classes)==1,"CH06_67_ORIGINAL_CLASS_MISSING")
    module=ast.Module(body=classes,type_ignores=[])
    ast.fix_missing_locations(module)
    context={"np":np}
    exec(compile(module,str(SOURCE),"exec"),context)
    return context["Planar2DOF"],hashlib.sha256(source.encode("utf-8")).hexdigest()


def bounded_dls(robot,target,initial, damping=0.15,alpha=0.5,
                max_step_rad=0.15, max_iter=400, tolerance_m=1e-3):
    """Test-only damped least squares, fail closed on unreachable target."""
    require(damping>0 and 0<alpha<=1 and max_step_rad>0,
            "CH06_67_BAD_DLS_PARAMETERS")
    theta=np.asarray(initial,dtype=np.float64).copy()
    goal=np.asarray(target,dtype=np.float64)
    max_applied=0.0
    goal_range=float(np.linalg.norm(goal))
    reach=robot.l1+robot.l2
    if goal_range>reach+1e-9:
        return {"status":"UNREACHABLE_REJECTED","steps":0,
                "max_step_rad":0.0,
                "final_error_m":float(np.linalg.norm(goal-robot.forward_kinematics(theta)[1])),
                "final_angles":theta.tolist()}
    for i in range(max_iter):
        ee=robot.forward_kinematics(theta)[1]
        error=goal-ee
        error_norm=float(np.linalg.norm(error))
        if error_norm<tolerance_m:
            return {"status":"CONVERGED","steps":i,
                    "max_step_rad":max_applied,
                    "final_error_m":error_norm,
                    "final_angles":theta.tolist()}
        J=robot.jacobian(theta)
        # Regularized Moore-Penrose pseudoinverse. No direct inverse of J.
        delta=J.T@np.linalg.solve(
            J@J.T+(damping*damping)*np.eye(2),error)
        delta*=alpha
        length=float(np.linalg.norm(delta))
        if not math.isfinite(length):
            raise RuntimeError("CH06_67_DLS_NONFINITE")
        if length>max_step_rad:
            delta*=max_step_rad/length
            length=max_step_rad
        max_applied=max(max_applied,length)
        theta+=delta
        require(np.isfinite(theta).all(),"CH06_67_DLS_NONFINITE_JOINTS")
    return {"status":"ITERATION_LIMIT","steps":max_iter,
            "max_step_rad":max_applied,
            "final_error_m":float(np.linalg.norm(goal-robot.forward_kinematics(theta)[1])),
            "final_angles":theta.tolist()}


def main():
    Book,source_sha=original_book_class()
    robot=Book(1.0,1.0)
    target=np.array([1.8,0.2],dtype=np.float64)
    original_theta=np.array([0.0,0.0],dtype=np.float64)
    J0=robot.jacobian(original_theta)
    singular_values=np.linalg.svd(J0,compute_uv=False)
    history,status=robot.inverse_kinematics_history(
        target,original_theta,alpha=0.5)
    require(status=="Divergence (Singularity!)" and len(history)==1,
            "CH06_67_ORIGINAL_SINGULARITY_NOT_REPRODUCED")
    require(abs(np.linalg.det(J0))<1e-12
            and singular_values[-1]<1e-12,
            "CH06_67_JACOBIAN_NOT_SINGULAR")
    print("CH06_67_ORIGINAL_JACOBIAN_SINGULARITY_REPRODUCED_PASS",flush=True)

    # Near-singular direct inverse is ill-conditioned, even though det>1e-4.
    near=np.array([0.0,0.001],dtype=np.float64)
    original_near,status_near=robot.inverse_kinematics_history(
        target,near,alpha=0.5)
    require(status_near=="Divergence (Explosion!)"
            and len(original_near)==2,
            "CH06_67_ORIGINAL_NEAR_SINGULAR_EXPLOSION_NOT_REPRODUCED")
    explosion_norm=float(np.linalg.norm(original_near[1]-original_near[0]))
    require(explosion_norm>2.5,"CH06_67_BAD_EXPLOSION_MAGNITUDE")
    print("CH06_67_ORIGINAL_INVERSE_EXPLOSION_REPRODUCED_PASS",flush=True)

    # Compare with bounded DLS, but do not silently modify original IK.
    dls=bounded_dls(robot,target,original_theta)
    require(dls["status"]=="CONVERGED"
            and dls["final_error_m"]<=.001
            and 0<dls["max_step_rad"]<=.150000000001,
            "CH06_67_BOUNDED_DLS_DID_NOT_CONVERGE")
    achieved=robot.forward_kinematics(np.array(dls["final_angles"]))[1]
    require(np.linalg.norm(achieved-target)<=.001,
            "CH06_67_DLS_FK_TARGET_MISMATCH")
    print(
       "CH06_67_DLS_BOUNDED_NUMERIC_RECOVERY_PASS "
       f"steps={dls['steps']} error_m={dls['final_error_m']:.7f} "
       f"max_step_rad={dls['max_step_rad']:.6f}",
       flush=True,
    )

    # Two analytical elbow choices for identical reachable XY goal.
    dual_target=np.array([1.0,1.0])
    up=np.array([0.0,math.pi/2])
    down=np.array([math.pi/2,-math.pi/2])
    errors=[float(np.linalg.norm(robot.forward_kinematics(t)[1]-dual_target))
            for t in (up,down)]
    require(max(errors)<1e-12 and np.linalg.norm(up-down)>2.0,
            "CH06_67_TWO_IK_SOLUTIONS_NOT_CONFIRMED")
    print("CH06_67_TWO_DISTINCT_SEEDS_SAME_FORWARD_KINEMATICS_PASS",flush=True)

    # Outside the 2x1m link reach, a solver must not claim convergence.
    unreachable=bounded_dls(robot,[2.2,0.2],original_theta)
    require(unreachable["status"]=="UNREACHABLE_REJECTED"
            and unreachable["steps"]==0,
            "CH06_67_WORKSPACE_GUARD_BYPASSED")
    print("CH06_67_UNREACHABLE_GOAL_REJECTED_WITHOUT_ACTUATION_PASS",flush=True)

    # Verify model limits from actual Ch06 book Xacro, not from the 2D toy.
    root=ET.parse(URDF).getroot()
    limits={}
    for joint in root.findall("joint"):
        lim=joint.find("limit")
        if lim is not None and joint.attrib.get("type")=="revolute":
            limits[joint.attrib["name"]]={
                k:float(lim.attrib[k]) for k in ("lower","upper","velocity")
            }
    require(len(limits)==5
            and set(limits)=={
               "joint1","joint2","joint3","joint4","joint_wrist"},
            "CH06_67_REAL_ARM_LIMITS_MISSING")
    for key,limit in limits.items():
        require(limit["lower"]<limit["upper"] and limit["velocity"]>0,
                "CH06_67_INVALID_BOOK_URDF_JOINT_LIMIT")
    require(limits["joint2"]["lower"]< -1.5
            and limits["joint2"]["upper"]<1.6
            and limits["joint3"]["upper"]<2.1,
            "CH06_67_REAL_URDF_LIMITS_DIFFER")
    print("CH06_67_ORIGINAL_FIVE_JOINT_LIMITS_IN_SOURCE_XACRO_PASS",flush=True)

    receipt={
       "chapter":"Ch06","section":"6.7","status":"SCOPED_PASS",
       "scenario":"original_2d_ik_failure_and_bounded_test_only_dls",
       "source_sha":os.environ.get("RUN_SOURCE_SHA","LOCAL_UNPINNED"),
       "original_source_sha256":source_sha,
       "original_source_unchanged":True,
       "original_singularity":{"status":status,
           "det_jacobian":float(np.linalg.det(J0)),
           "min_singular_value":float(singular_values[-1]),
           "history_points":len(history)},
       "original_explosion":{"status":status_near,
           "angle_jump_norm_rad":explosion_norm,
           "history_points":len(original_near)},
       "test_only_dls":dls,
       "two_elbow_solutions_fk_error_m":errors,
       "unreachable_status":unreachable["status"],
       "book_original_xacro_joint_limits":limits,
       "original_gui_slider_and_rollback":"NOT_RUN",
       "collision_planning_scene":"NOT_RUN",
       "ik_solver_ros_integration":"NOT_RUN",
       "physical_robot":"NOT_RUN",
       "ch06_64_65_66_retest":"NOT_RUN",
       "ch07_rgbd":"BLOCKED",
       "ch10":"HOLD",
    }
    targetfile=OUT/"receipt.json"
    with targetfile.open("x",encoding="utf-8") as f:
        json.dump(receipt,f,indent=2,sort_keys=True,ensure_ascii=False)
        f.write("\n");f.flush();os.fsync(f.fileno())
    print("CH06_67_ORIGINAL_IK_FAILURE_AND_TEST_ONLY_RECOVERY_SCOPED_PASS",flush=True)


if __name__=="__main__":
    main()
