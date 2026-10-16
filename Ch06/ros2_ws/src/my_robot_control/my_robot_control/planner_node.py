# my_robot_control/planner_node.py
import os
import yaml

import rclpy
from rclpy.node import Node

from ament_index_python.packages import get_package_share_directory

from moveit_configs_utils import MoveItConfigsBuilder
from moveit.planning import MoveItPy


class PlannerNode(Node):
    def __init__(self):
        super().__init__("planner_node")
        self.declare_parameter("planning_group",
            "arm_group"
        )
        self.declare_parameter(
            "goal_name",
            "ready"
        )

        self.moveit_params = self._build_moveit_params()

        self.get_logger().info(
            "MoveIt configuration loaded"
        )
        self.get_logger().info(
            f"Planning Pipelines : "
            f"{self.moveit_params['planning_pipelines']}"
        )
        self.get_logger().info(
            f"OMPL Plugins : "
            f"{self.moveit_params['ompl']['planning_plugins']}"
        )
        self._moveit = MoveItPy(
            node_name="my_robot_planner_moveit",
            config_dict=self.moveit_params,
        )
        self._run_once()

    def _build_moveit_params(self):
        share_dir = get_package_share_directory(
            "my_robot_moveit_config"
        )
        config_dir = os.path.join(
            share_dir,
            "config"
        )
        moveit_config = (
            MoveItConfigsBuilder(
                robot_name="my_robot",
                package_name="my_robot_moveit_config",
            )
            .robot_description(
                file_path="config/my_robot.urdf.xacro"
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
            .planning_pipelines(
                pipelines=["ompl"]
            )
            .to_moveit_configs()
        )

        params = moveit_config.to_dict()

        # OMPL Planning Config 추가
        ompl_yaml = os.path.join(
            config_dir,
            "ompl_planning.yaml"
        )

        with open(ompl_yaml, "r") as f:
            ompl_config = yaml.safe_load(f)

        # 중요: MoveItPy는 ompl namespace를 기대함
        params["ompl"] = ompl_config
        # Planning Pipeline
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
        # 기본 Planner
        params["plan_request_params"] = {
            "planning_pipeline": "ompl",
            "planner_id": "RRTConnectkConfigDefault",
            "planning_attempts": 1,
            "planning_time": 5.0,
            "max_velocity_scaling_factor": 1.0,
            "max_acceleration_scaling_factor": 1.0,
        }
        return params

    def _run_once(self):
        planning_group = (
            self.get_parameter(
                "planning_group"
            ).value
        )
        goal_name = (
            self.get_parameter(
                "goal_name"
            ).value
        )
        self.get_logger().info(
            f"Planning Group : {planning_group}"
        )
        self.get_logger().info(
            f"Goal State : {goal_name}"
        )
        planning_component = (
            self._moveit.get_planning_component(
                planning_group
            )
        )

        # 현재 상태를 시작점으로 설정
        planning_component.set_start_state_to_current_state()

        # SRDF Named State 사용
        planning_component.set_goal_state(
            configuration_name=goal_name
        )

        self.get_logger().info(
            "Start Planning..."
        )

        plan_result = planning_component.plan()

        if not plan_result:
            self.get_logger().error(
                "Planning Failed"
            )
            return

        self.get_logger().info(
            "Planning Success"
        )
        self.get_logger().info(
            "Execute Trajectory..."
        )
        self._moveit.execute(
            plan_result.trajectory,
            controllers=[]
        )
        self.get_logger().info(
            "Execution Request Sent"
        )

def main():

    rclpy.init()
    node = PlannerNode()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()