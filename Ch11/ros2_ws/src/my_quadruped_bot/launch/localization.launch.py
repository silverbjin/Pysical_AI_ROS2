"""One local TF authority and physical simulation odometry observations."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory('my_quadruped_bot'), 'config', 'ekf.yaml')
    return LaunchDescription([
        Node(package='my_quadruped_bot', executable='sim_odometry',
             name='sim_odometry', output='screen', parameters=[{'use_sim_time': True}]),
        Node(package='robot_localization', executable='ekf_node',
             name='ekf_filter_node', output='screen', parameters=[config],
             remappings=[('/odometry/filtered', '/odom')]),
    ])
