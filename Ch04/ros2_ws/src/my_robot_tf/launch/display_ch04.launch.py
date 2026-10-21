"""4.5절: Ch03의 실제 two_dof_arm 모델을 사용하는 RSP/GUI/RViz 데모.

사전 조건: Ch03/ros2_ws 빌드와 source를 먼저 수행한다.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    model_dir = get_package_share_directory("my_robot_description")
    xacro_file = os.path.join(model_dir, "urdf", "two_dof_arm.urdf.xacro")
    if not os.path.isfile(xacro_file):
        raise FileNotFoundError(
            f"Ch03 two_dof_arm URDF not found: {xacro_file}; "
            "build and source Ch03/ros2_ws first"
        )

    config = os.path.join(
        get_package_share_directory("my_robot_tf"),
        "rviz", "display_ch04.rviz",
    )
    description = ParameterValue(Command(["xacro ", xacro_file]), value_type=str)
    return LaunchDescription([
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            parameters=[{"robot_description": description, "use_sim_time": False}],
            output="screen",
        ),
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            name="joint_state_publisher_gui",
            output="screen",
        ),
        Node(
            package="rviz2", executable="rviz2",
            arguments=["-d", config], output="screen",
        ),
    ])
