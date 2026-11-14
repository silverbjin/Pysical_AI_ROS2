#!/usr/bin/env python3
"""Generate MoveIt params from SAME expanded G03 GazeboSimSystem URDF.

Not Ch07's legacy FakeSystem RViz demo Xacro. External G03 launch is headless.
"""
import argparse
import json
from pathlib import Path
import yaml
from moveit_configs_utils import MoveItConfigsBuilder


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--robot",required=True,type=Path)
    a.add_argument("--out",required=True,type=Path)
    a.add_argument("--receipt",required=True,type=Path)
    args=a.parse_args()
    urdf=args.robot.read_text()
    assert "gz_ros2_control/GazeboSimSystem" in urdf
    assert "mock_components/GenericSystem" not in urdf
    cfg=(MoveItConfigsBuilder("my_robot",package_name="my_robot_moveit_config")
         .robot_description(file_path=str(args.robot))
         .trajectory_execution(file_path="config/moveit_controllers.yaml")
         .planning_pipelines(pipelines=["ompl"])
         .to_moveit_configs())
    params=cfg.to_dict()
    assert "robot_description" in params and "robot_description_semantic" in params
    assert "robot_description_kinematics" in params
    assert "planning_pipelines" in params
    # MoveItConfigsBuilder may pick the package's legacy fake/RViz
    # my_robot.urdf.xacro instead of the explicit G00 Gazebo composition.
    # Override ONLY the planner's robot_description with the exact expanded
    # bytes already passed to RSP and Gazebo, not a second Xacro expansion.
    builder_uses_same_urdf=(urdf.strip()==params["robot_description"].strip())
    params["robot_description"]=urdf
    assert "mock_components/GenericSystem" not in params["robot_description"]
    assert "gz_ros2_control/GazeboSimSystem" in params["robot_description"]
    # ROS 2 Jazzy / MoveIt issue #2940: a late /clock QoS parameter
    # declaration can be rejected by MoveGroup's dynamic-parameter callback,
    # aborting after the planner loads. Make the read-only ClockQoS defaults
    # startup overrides, not a post-start parameter change. The values below
    # match the standard clock subscriber profile; no QoS is relaxed.
    clock_qos = {
        "qos_overrides./clock.subscription.depth": 1,
        "qos_overrides./clock.subscription.durability": "volatile",
        "qos_overrides./clock.subscription.history": "keep_last",
        "qos_overrides./clock.subscription.reliability": "best_effort",
    }
    params.update(clock_qos)
    params["use_sim_time"]=True
    assert all(params[k] == v for k,v in clock_qos.items())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(yaml.safe_dump({"move_group":{"ros__parameters":params}},
                                        sort_keys=False,allow_unicode=True))
    receipt={"status":"STATIC_PASS",
             "scope":"G03_SAME_EXPANDED_GAZEBO_ROBOT_IN_RSP_AND_MOVE_GROUP",
             "gazebo_urdf_exact_bytes":True,
             "builder_original_model_matches":builder_uses_same_urdf,
             "builder_description_overridden_from_gazebo_urdf":not builder_uses_same_urdf,
             "semantic_srdf":True,
             "kinematics_configured":True,
             "planning_pipeline":"ompl",
             "clock_qos_startup_overrides":clock_qos,
             "moveit_2940_workaround":"STARTUP_ONLY_NOT_RUNTIME_MUTATION",
             "actual_moveit_planning":"NOT_RUN",
             "actual_motor_commands":0,
             "Ch10":"HOLD"}
    args.receipt.write_text(json.dumps(receipt,indent=2)+"\n")
    print("CH07_77_G03_EXACT_GAZEBO_URDF_MOVEIT_PARAMS_STATIC_PASS")

if __name__=="__main__":
    main()
