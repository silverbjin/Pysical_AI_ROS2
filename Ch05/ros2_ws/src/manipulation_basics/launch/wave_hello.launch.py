"""Start the Hello Robot publisher against an already running Gazebo arm."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='manipulation_basics', executable='wave_hello',
             name='wave_hello_node', parameters=[{'use_sim_time': True}],
             output='screen'),
    ])
