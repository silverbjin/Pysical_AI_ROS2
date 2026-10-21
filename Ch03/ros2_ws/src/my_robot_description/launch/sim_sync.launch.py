"""Simulated robot and RViz, reusing the canonical Ch03 spawn launch.

The included spawn_robot.launch.py owns the Gazebo world, robot_state_publisher,
robot creation, and ros_gz_bridge; avoid duplicate publishers and stale world names.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('my_robot_description')
    spawn_launch = os.path.join(pkg_share, 'launch', 'spawn_robot.launch.py')
    rviz_config = os.path.join(pkg_share, 'rviz', 'display.rviz')

    gazebo_robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(spawn_launch)
    )
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{
            'use_sim_time': ParameterValue(
                LaunchConfiguration('use_sim_time'), value_type=bool
            )
        }],
        output='screen',
    )
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use Gazebo simulation clock in RViz'
        ),
        gazebo_robot,
        rviz,
    ])
