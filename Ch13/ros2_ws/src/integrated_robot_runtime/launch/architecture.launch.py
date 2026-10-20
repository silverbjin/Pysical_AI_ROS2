"""Launch separate runtime processes against an already running section 13.2 engine."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    clock = {'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)}
    delay = {'processing_delay_s': ParameterValue(
        LaunchConfiguration('processing_delay_s'), value_type=float)}
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('processing_delay_s', default_value='0.2'),
        *[Node(package='integrated_robot_runtime', executable=name,
               output='screen', parameters=[clock])
          for name in ('locomotion_node', 'manipulation_node', 'mission_commander')],
        Node(package='integrated_robot_runtime', executable='vision_processor',
             output='screen', parameters=[clock, delay]),
        Node(package='integrated_robot_runtime', executable='state_manager',
             output='screen', parameters=[clock]),
    ])
