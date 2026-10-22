"""Launch separate runtime processes against an already running section 13.2 engine."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from integrated_robot_vision.trace import trace_options


def launch_nodes(context):
    trace = trace_options(LaunchConfiguration('trace_enabled', default='false').perform(context),
                          LaunchConfiguration('trace_run_id', default='').perform(context))
    clock = {'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time', default='true'), value_type=bool)}
    delay = {'processing_delay_s': ParameterValue(
        LaunchConfiguration('processing_delay_s', default='0.2'), value_type=float)}
    return [*[Node(package='integrated_robot_runtime', executable=name,
               output='screen', parameters=([clock, {'allow_camera_motion_test': ParameterValue(
                   LaunchConfiguration('allow_camera_motion_test', default='false'), value_type=bool)}, trace]
                   if name == 'manipulation_node' else [clock]))
          for name in ('locomotion_node', 'manipulation_node', 'mission_commander')],
        Node(package='integrated_robot_runtime', executable='vision_processor',
             output='screen', parameters=[clock, delay],
             condition=IfCondition(LaunchConfiguration('include_demo_vision', default='true'))),
        Node(package='integrated_robot_runtime', executable='state_manager',
             output='screen', parameters=[clock, {'wait_for_controllers': ParameterValue(
                 LaunchConfiguration('wait_for_controllers', default='false'), value_type=bool)}])]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('processing_delay_s', default_value='0.2'),
        DeclareLaunchArgument('include_demo_vision', default_value='true'),
        DeclareLaunchArgument('wait_for_controllers', default_value='false'),
        DeclareLaunchArgument('allow_camera_motion_test', default_value='false'),
        DeclareLaunchArgument('trace_enabled', default_value='false'),
        DeclareLaunchArgument('trace_run_id', default_value=''),
        OpaqueFunction(function=launch_nodes)])
