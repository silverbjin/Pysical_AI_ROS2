#!/usr/bin/env python3
import time
import yaml
import os
import gc # 안정적인 종료

import rclpy

from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder

from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped


def build_moveit_config():
    package_name = "my_robot_moveit_config"
    pkg_share = get_package_share_directory(package_name)
    config_dir = os.path.join(pkg_share, "config")

    # 기본 MoveIt 설정 로드
    moveit_config = (
        MoveItConfigsBuilder(
            robot_name="my_robot",
            package_name=package_name,
        )
        .robot_description(
            file_path="urdf/my_robot.urdf"
        )
        .robot_description_semantic(
            file_path="config/my_robot.srdf"
        )
        .robot_description_kinematics(
            file_path="config/kinematics.yaml"
        )
        .joint_limits(
            file_path="config/joint_limits.yaml"
        )
        .trajectory_execution(
            file_path="config/moveit_controllers.yaml"
        )
        .to_moveit_configs()
    )

    params = moveit_config.to_dict()

    # OMPL 설정 로드
    ompl_file = os.path.join(
        config_dir,
        "ompl_planning.yaml"
    )

    with open(ompl_file, "r") as f:
        ompl_config = yaml.safe_load(f)

    # MoveItPy가 기대하는 구조 생성
    params["ompl"] = ompl_config
    params["planning_pipelines"] = {
        "pipeline_names": ["ompl"],
        "default_planning_pipeline": "ompl",
    }
    # Planning Scene Monitor
    params["planning_scene_monitor_options"] = {
        "name": "planning_scene_monitor",
        "robot_description": "robot_description",
        "joint_state_topic": "/joint_states",
        "wait_for_initial_state_timeout": 10.0,
    }
    # 기본 Planner 설정
    params["plan_request_params"] = {
        "planning_pipeline": "ompl",
        "planner_id": "RRTConnectkConfigDefault",
        "planning_attempts": 1,
        "planning_time": 5.0,
        "max_velocity_scaling_factor": 1.0,
        "max_acceleration_scaling_factor": 1.0,
    }
    return params


def main():
    rclpy.init()
    print("=== MoveIt Config Loading ===")

    moveit_config = build_moveit_config()
    print("\n=== Planning Pipeline ===")
    print(moveit_config["planning_pipelines"])
    print("\n=== OMPL Plugin ===")
    print(moveit_config["ompl"]["planning_plugins"])

    # MoveItPy 생성
    my_robot = MoveItPy(
        node_name="hello_moveit",
        config_dict=moveit_config,
    )
    # arm_group 획득
    arm = my_robot.get_planning_component(
        "arm_group"
    )
    # 초기화 대기
    # time.sleep(1.0)
    time.sleep(2.0)
    
    print("\n=== Robot Ready ===")
    ##################################################
    # Task 1 : Named State
    ##################################################
    print("\n[Task 1] Move To Named State")
    arm.set_start_state_to_current_state()
    arm.set_goal_state(
        configuration_name="ready"
    )
    plan_result = arm.plan()

    if plan_result:
        print("Planning Success")
        my_robot.execute(
            plan_result.trajectory,
            controllers=[]
        )
        print("Execution Success")
    else:
        print("Planning Failed")
    time.sleep(2.0)

    ##################################################
    # Task 2 : IK Goal
    ##################################################
    print("\n[Task 2] IK Planning")
    pose_goal = PoseStamped()
    pose_goal.header.frame_id = "base_link"
    pose_goal.pose.position.x = 0.00
    pose_goal.pose.position.y = 0.00
    pose_goal.pose.position.z = 2.1
    pose_goal.pose.orientation.x = 0.0
    pose_goal.pose.orientation.y = 0.0
    pose_goal.pose.orientation.z = 0.0
    pose_goal.pose.orientation.w = 1.0
    arm.set_start_state_to_current_state()
    arm.set_goal_state(
        pose_stamped_msg=pose_goal,
        pose_link="link_wrist"
    )
    plan_result = arm.plan()

    if plan_result:
        print("IK Planning Success")
        my_robot.execute(
            plan_result.trajectory,
            controllers=[]
        )
        print("IK Execution Success")
    else:
        print("IK Planning Failed")
        
    # 종료 전 대기    
    time.sleep(2.0)
    print("\n=== Finished ===")         
    
    
    del my_robot    
    gc.collect()
        
    rclpy.shutdown()
    os._exit(0)

if __name__ == "__main__":
    main()