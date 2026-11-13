#!/usr/bin/env python3
"""Ch06 §6.4 scoped pose IK: FK-derived reachable pose -> plan -> execute -> FK.

SIMULATION ONLY. Reuses the already-accepted MoveIt model, ROS observation,
and mock-only MoveItPy teardown workaround from hello_moveit.py.
It does not claim Gazebo physics, general 6-DoF IK, or physical robot safety.
"""
import json
import math
import os
from pathlib import Path
import sys
import time

from geometry_msgs.msg import PoseStamped
from moveit.core.robot_state import RobotState
from moveit.planning import MoveItPy
import rclpy

from my_robot_control.hello_moveit import (
    ARM_JOINTS, JointStateObserver, build_moveit_config,
)

# Fixed, non-singular, URDF-bounded 5-joint configuration. This is NOT a
# hard-coded Cartesian pose: the current installed MoveIt RobotState
# computes the target position and orientation from these joint angles.
# Keep a meaningful move away from the mock controller's zero start.
FK_SEED_JOINTS = {
    "joint1": 0.25, "joint2": -0.25, "joint3": 0.95,
    "joint4": 0.20, "joint_wrist": -0.15,
}
TIP = "link_wrist"
FRAME = "world"  # Installed Ch06 URDF root link and fixed SRDF virtual frame.
MAX_POSITION_ERROR_M = 0.03
MAX_ORIENTATION_ERROR_RAD = 0.10
MIN_MOVEMENT_RAD = 0.10
MIN_TARGET_TRANSLATION_M = 0.08


def pose_from_joints(robot_model, joints):
    """Independent FK from observed joint values, not commanded trajectory."""
    state = RobotState(robot_model)
    state.set_to_default_values()
    if set(joints) != set(ARM_JOINTS):
        raise ValueError("CH06_POSE_INCOMPLETE_ARM_JOINTS")
    state.joint_positions = {key: float(joints[key]) for key in ARM_JOINTS}
    state.update()
    return state.get_pose(TIP)


def pose_error(actual, target):
    dp = ((actual.position.x - target.position.x) ** 2
          + (actual.position.y - target.position.y) ** 2
          + (actual.position.z - target.position.z) ** 2) ** 0.5
    a = actual.orientation
    b = target.orientation
    qa = (a.x, a.y, a.z, a.w)
    qb = (b.x, b.y, b.z, b.w)
    na = math.sqrt(sum(v * v for v in qa))
    nb = math.sqrt(sum(v * v for v in qb))
    if min(na, nb) < 0.999 or max(na, nb) > 1.001:
        raise RuntimeError("CH06_POSE_INVALID_FK_QUATERNION")
    dot = abs(sum(x * y for x, y in zip(qa, qb)) / (na * nb))
    angle = 2.0 * math.acos(min(1.0, max(0.0, dot)))
    if not all(map(math.isfinite, (dp, angle))):
        raise RuntimeError("CH06_POSE_NONFINITE_ERROR")
    return dp, angle


def run_pose_fk(robot, observer):
    # Measured readiness: this is a new process, not the already-accepted
    # named ready test. Give MoveItCpp its own fresh /joint_states stream.
    before = observer.wait_for(lambda _: True, timeout_sec=15.0)
    first_count = observer.messages
    warmup_until = time.monotonic() + 3.0
    while time.monotonic() < warmup_until:
        rclpy.spin_once(observer, timeout_sec=0.25)
    age = (observer.get_clock().now().nanoseconds
           - (observer.last_stamp_ns or 0)) / 1e9
    new_samples = observer.messages - first_count
    if new_samples < 20 or not (-0.5 <= age <= 1.0):
        raise RuntimeError(
            f"CH06_POSE_JOINT_STREAM_STALE samples={new_samples} age={age:.3f}"
        )
    print(f"CH06_POSE_JOINT_STREAM_READY samples={new_samples}", flush=True)

    model = robot.get_robot_model()
    # The target must be produced by REAL MoveIt FK for this exact model.
    target = pose_from_joints(model, FK_SEED_JOINTS)
    initial = pose_from_joints(model, before)
    displacement, _ = pose_error(initial, target)
    if displacement < MIN_TARGET_TRANSLATION_M:
        raise RuntimeError(
            f"CH06_POSE_TARGET_NOT_DISTINCT_FROM_INITIAL displacement={displacement:.4f}"
        )
    print(
        f"CH06_POSE_FK_TARGET_CREATED frame={FRAME} tip={TIP} "
        f"xyz=({target.position.x:.5f},{target.position.y:.5f},"
        f"{target.position.z:.5f}) initial_translation_m={displacement:.5f}",
        flush=True,
    )

    stamped = PoseStamped()
    stamped.header.frame_id = FRAME
    stamped.header.stamp = observer.get_clock().now().to_msg()
    stamped.pose = target
    planning = robot.get_planning_component("arm_group")
    planning.set_start_state_to_current_state()
    accepted = planning.set_goal_state(
        pose_stamped_msg=stamped, pose_link=TIP,
    )
    if not accepted:
        raise RuntimeError("CH06_POSE_IK_GOAL_REJECTED")
    print("CH06_POSE_IK_GOAL_ACCEPTED", flush=True)
    result = planning.plan()
    if not result:
        raise RuntimeError("CH06_POSE_IK_PLANNING_FAIL")
    print("CH06_POSE_IK_PLANNING_PASS", flush=True)

    execution = robot.execute(result.trajectory, controllers=[])
    status = str(execution.status)
    print(f"CH06_POSE_IK_EXECUTION_STATUS={status}", flush=True)
    if not bool(execution) or status.upper() != "SUCCEEDED":
        raise RuntimeError(f"CH06_POSE_IK_EXECUTION_FAIL status={status}")

    count_before = observer.messages
    def reached(joints):
        if observer.messages <= count_before:
            return False
        dp, da = pose_error(pose_from_joints(model, joints), target)
        return dp <= MAX_POSITION_ERROR_M and da <= MAX_ORIENTATION_ERROR_RAD

    observed = observer.wait_for(reached, timeout_sec=12.0)
    final_pose = pose_from_joints(model, observed)
    pos_error, angle_error = pose_error(final_pose, target)
    joint_movement = max(abs(observed[j] - before[j]) for j in ARM_JOINTS)
    if joint_movement < MIN_MOVEMENT_RAD:
        raise RuntimeError("CH06_POSE_IK_NO_MEASURED_JOINT_MOVEMENT")
    print(
        "CH06_POSE_IK_EXECUTION_FK_FEEDBACK_PASS "
        f"position_error_m={pos_error:.6f} "
        f"orientation_error_rad={angle_error:.6f} "
        f"joint_movement_rad={joint_movement:.6f}",
        flush=True,
    )
    return {
        "chapter": "Ch06", "section": "6.4",
        "scenario": "fk_derived_pose_ik_mock_only",
        "planning": "PASS", "execution": status, "pose_ik": "PASS",
        "observed_fk": "PASS", "frame": FRAME, "tip": TIP,
        "fk_seed_joint_positions": FK_SEED_JOINTS,
        "measured_joint_positions": observed,
        "target_pose": {
            "position": [target.position.x, target.position.y, target.position.z],
            "quaternion_xyzw": [target.orientation.x, target.orientation.y,
                                target.orientation.z, target.orientation.w],
        },
        "position_error_m": pos_error,
        "orientation_error_rad": angle_error,
        "joint_movement_rad": joint_movement,
        "initial_target_translation_m": displacement,
        "max_position_error_m": MAX_POSITION_ERROR_M,
        "max_orientation_error_rad": MAX_ORIENTATION_ERROR_RAD,
        "normal_moveitcpp_destructor": "NOT_RUN_UPSTREAM_MOVEIT2_3721",
        "named_ready_retest": "NOT_RUN_PRESERVED_CI_43338734506",
        "gazebo_physics": "NOT_RUN",
        "rviz_gui": "NOT_RUN",
        "real_hardware": "NOT_RUN",
        "general_6d_ik": "NOT_CLAIMED",
    }


def main(args=None):
    import argparse
    parser = argparse.ArgumentParser(description="Scoped FK-derived MoveItPy pose IK.")
    parser.add_argument("--ci-mock-verified-exit", action="store_true")
    known, ros_args = parser.parse_known_args(args)
    if not known.ci_mock_verified_exit or (
        os.environ.get("CH06_CI_MOCK_CONTROLLER_VERIFIED") != "1"
        or not os.environ.get("CH06_CI_RESULT_RECEIPT")
    ):
        print("CH06_POSE_MOCK_ONLY_EXIT_REQUIRED: no unverified controller",
              file=sys.stderr, flush=True)
        return 2
    robot = None
    observer = None
    rclpy.init(args=ros_args)
    try:
        config = build_moveit_config()
        observer = JointStateObserver()
        observer.wait_for(lambda _: True, timeout_sec=15.0)
        robot = MoveItPy(node_name="ch06_pose_ik_fk", config_dict=config)
        receipt_data = run_pose_fk(robot, observer)

        # Keep the same explicit, fake-hardware-only workaround as the
        # accepted #133 path. Receipt is written only AFTER measured FK PASS.
        receipt = Path(os.environ["CH06_CI_RESULT_RECEIPT"])
        receipt.parent.mkdir(parents=True, exist_ok=True)
        temp = receipt.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(receipt_data, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, receipt)
        print("CH06_POSE_IK_SCOPED_PASS_MOCK_ONLY", flush=True)
        print("CH06_POSE_UPSTREAM_3721_TEARDOWN_BYPASSED_AFTER_FK_PASS", flush=True)
        observer.destroy_node()
        observer = None
        if rclpy.ok():
            rclpy.shutdown()
        sys.stdout.flush()
        sys.stderr.flush()
        os.execv("/usr/bin/true", ["true"])
        raise AssertionError("execv unexpectedly returned")
    except (Exception, KeyboardInterrupt) as exc:
        print(f"CH06_POSE_IK_FAIL type={type(exc).__name__} reason={exc}",
              file=sys.stderr, flush=True)
        return 1
    finally:
        if robot is not None:
            del robot
        if observer is not None:
            observer.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
