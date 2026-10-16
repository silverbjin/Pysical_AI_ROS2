"""Simulation, sensors and localization with one EKF TF authority."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('my_quadruped_bot')
    includes = [IncludeLaunchDescription(PythonLaunchDescriptionSource(
        os.path.join(share, 'launch', name))) for name in
        ('simulation.launch.py', 'localization.launch.py')]
    nodes = [Node(package='my_quadruped_bot', executable=name,
                  output='screen', parameters=[{'use_sim_time': True}])
             for name in ('trot_controllerFSM', 'imu_processor', 'lidar_safety')]
    return LaunchDescription(includes + nodes)
