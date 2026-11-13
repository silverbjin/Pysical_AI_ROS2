"""Ch06 §6.4 bounded headless MoveItPy + fake ros2_control demo.

This launch intentionally does NOT start RViz or Gazebo; actual trajectories
are executed by ros2_control mock_components/GenericSystem, with measured
/joint_states. It is not physical Gazebo or hardware acceptance.
"""
from launch import LaunchDescription
from launch.actions import RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node

from my_robot_control.hello_moveit import build_moveit_config
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def generate_launch_description():
    params = build_moveit_config()
    # Use the exact same robot_description as the MoveItPy client.
    controller_yaml = str(
        Path(get_package_share_directory("my_robot_moveit_config"))
        / "config" / "ros2_controllers.yaml"
    )
    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": params["robot_description"],
                     "use_sim_time": False}],
    )
    control = Node(
        package="controller_manager",
        executable="ros2_control_node",
        output="screen",
        parameters=[{"robot_description": params["robot_description"]},
                    controller_yaml],
    )
    broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "-c", "/controller_manager",
                   "--controller-manager-timeout", "45"],
        output="screen",
    )
    arm = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_group_controller", "-c", "/controller_manager",
                   "--controller-manager-timeout", "45"],
        output="screen",
    )
    return LaunchDescription([rsp, control, broadcaster, arm])
