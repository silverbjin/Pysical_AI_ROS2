"""Gazebo and RViz composition for book figure 11-2; no velocity commands."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('my_quadruped_bot')
    return LaunchDescription([
        DeclareLaunchArgument('start_controller', default_value='true',
                              description='Run the existing FSM to stand; no cmd_vel is sent.'),
        DeclareLaunchArgument('start_rviz', default_value='true'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(share, 'launch', 'simulation.launch.py')),
            launch_arguments={'world': os.path.join(
                share, 'worlds', 'sensor_figure_world.sdf')}.items()),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(share, 'launch', 'localization.launch.py'))),
        Node(package='my_quadruped_bot', executable='trot_controllerFSM',
             output='screen', parameters=[{'use_sim_time': True}],
             condition=IfCondition(LaunchConfiguration('start_controller'))),
        Node(package='my_quadruped_bot', executable='imu_pose_viz',
             output='screen', parameters=[{'use_sim_time': True}]),
        Node(package='rviz2', executable='rviz2', name='figure_11_2_rviz',
             arguments=['-d', os.path.join(share, 'rviz', 'figure_11_2.rviz')],
             parameters=[{'use_sim_time': True}],
             condition=IfCondition(LaunchConfiguration('start_rviz'))),
    ])
