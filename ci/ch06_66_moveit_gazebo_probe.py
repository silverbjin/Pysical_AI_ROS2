#!/usr/bin/env python3
"""Ch06 §6.6: real MoveItPy OMPL plan -> real GazeboSimSystem controller.

Run only inside a preflight-verified Gazebo controller simulation. The
controller-only action accepted in #137 is NOT repeated here; the new
boundary is MoveItPy's own plan/execute against the same Gazebo hardware.
No GUI, gripper, real robot or normal MoveItPy destructor acceptance.
"""
import json
import os
from pathlib import Path
import sys

import rclpy
import xacro
from ament_index_python.packages import get_package_share_directory
from moveit.planning import MoveItPy

from my_robot_control.hello_moveit import (
    ARM_JOINTS, JointStateObserver, build_moveit_config, run_named_ready,
)


def gazebo_moveit_config():
    path = (Path(get_package_share_directory("my_robot_description"))
            / "urdf" / "my_robot.ros2_control_gazebo.urdf.xacro")
    if not path.is_file():
        raise FileNotFoundError("CH06_66_GAZEBO_XACRO_NOT_INSTALLED")
    cfg = build_moveit_config()  # accepted #133 OMPL parameters and model contract
    # EXACT gazebo wrapper loaded by Gazebo_moveit.launch.py, not fake Xacro.
    cfg["robot_description"] = xacro.process_file(str(path)).toxml()
    cfg["use_sim_time"] = True
    if "gz_ros2_control/GazeboSimSystem" not in cfg["robot_description"]:
        raise RuntimeError("CH06_66_GAZEBO_MODEL_CONTRACT_MISMATCH")
    if "mock_components/GenericSystem" in cfg["robot_description"]:
        raise RuntimeError("CH06_66_FAKE_HARDWARE_DESCRIPTION_FORBIDDEN")
    return cfg


def main():
    if (os.environ.get("CH06_66_GAZEBO_VERIFIED") != "1"
            or not os.environ.get("CH06_66_MOVEIT_RECEIPT")):
        print("CH06_66_GAZEBO_HARDWARE_PREFLIGHT_REQUIRED", flush=True)
        return 2

    # Both Python observer and MoveItCpp get the same advancing /clock.
    rclpy.init(args=["--ros-args", "-p", "use_sim_time:=true"])
    robot = None
    observer = None
    try:
        cfg = gazebo_moveit_config()
        print("CH06_66_GAZEBO_MOVEIT_SAME_URDF_AND_SIM_CLOCK_CONFIG_PASS",
              flush=True)
        observer = JointStateObserver()
        observer.wait_for(lambda _: True, timeout_sec=15.0)
        robot = MoveItPy(
            node_name="ch06_66_moveit_to_gazebo",
            config_dict=cfg,
        )
        # This code path is accepted as a MoveItPy named-state implementation
        # in #133; here its execution target is verified actual GazeboSimSystem.
        errors = run_named_ready(robot, observer)
        max_error = max(errors.values())
        if max_error > 0.06 or len(errors) != len(ARM_JOINTS):
            raise RuntimeError("CH06_66_GAZEBO_MOVEIT_FK_ERROR_ABOVE_TOLERANCE")
        print(
            "CH06_66_MOVEIT_OMPL_PLAN_GAZEBO_ACTION_AND_JOINT_FEEDBACK_PASS "
            f"max_joint_error_rad={max_error:.6f}",
            flush=True,
        )
        receipt = Path(os.environ["CH06_66_MOVEIT_RECEIPT"])
        receipt.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "chapter": "Ch06", "section": "6.6",
            "scope": "moveitpy_ompl_plan_execute_real_gazebo_gz_ros2_control",
            "gazebo_model": str(Path(get_package_share_directory(
                "my_robot_description"))
                / "urdf" / "my_robot.ros2_control_gazebo.urdf.xacro"),
            "use_sim_time": True,
            "planning": "PASS",
            "execution": "SUCCEEDED",
            "joint_goal": "PASS",
            "per_joint_error_rad": errors,
            "max_joint_error_rad": max_error,
            "controller_hardware": "REQUIRES_INDEPENDENT_GAZEBO_PLUGIN_PREFLIGHT",
            "controller_only_previous_case": "NOT_RERUN_CI_43346594160",
            "moveitpy_destructor": "NOT_RUN_UPSTREAM_MOVEIT2_3721",
            "rviz_gui": "NOT_RUN",
            "real_hardware": "NOT_RUN",
            "gripper": "NOT_RUN",
            "ch10": "HOLD",
        }
        temp = receipt.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, receipt)
        print("CH06_66_MOVEIT_TO_GAZEBO_SCOPED_PASS", flush=True)
        print("CH06_66_UPSTREAM_3721_TEARDOWN_NOT_RUN_AFTER_GAZEBO_VERIFIED_PASS",
              flush=True)
        observer.destroy_node()
        observer = None
        if rclpy.ok():
            rclpy.shutdown()
        sys.stdout.flush()
        sys.stderr.flush()
        # ONLY CI-verified simulation Gazebo hardware, evidence already saved.
        # Do not run this mock-style workaround on actual robot hardware.
        os.execv("/usr/bin/true", ["true"])
        raise AssertionError("execv unexpectedly returned")
    except (Exception, KeyboardInterrupt) as exc:
        print(f"CH06_66_MOVEIT_FAIL type={type(exc).__name__} reason={exc}",
              flush=True)
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
