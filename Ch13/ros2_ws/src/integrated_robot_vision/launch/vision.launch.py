"""Observation-only RGB-D pipeline. No arm/leg command producer lives here."""
import math
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from integrated_robot_vision.trace import trace_options


def launch_nodes(context):
    backend = LaunchConfiguration('detector_backend').perform(context)
    weights = LaunchConfiguration('weights_path').perform(context)
    delay = float(LaunchConfiguration('processing_delay_s').perform(context))
    rate = float(LaunchConfiguration('max_rate_hz', default='10').perform(context))
    clock = LaunchConfiguration('use_sim_time').perform(context).lower()
    if backend not in ('yolo', 'color_fixture') or clock not in ('true', 'false'):
        raise ValueError('explicit supported backend and boolean clock required')
    if backend == 'yolo' and (not Path(weights).is_absolute() or not Path(weights).is_file()):
        raise ValueError('yolo requires an existing absolute weights_path; no download/fallback')
    if not math.isfinite(delay) or delay < 0:
        raise ValueError('finite nonnegative inference delay required')
    if not math.isfinite(rate) or not 0 < rate <= 15:
        raise ValueError('max_rate_hz must be finite and in (0,15]')
    trace = trace_options(LaunchConfiguration('trace_enabled', default='false').perform(context),
                          LaunchConfiguration('trace_run_id', default='').perform(context))
    shared = {'use_sim_time': clock == 'true', **trace}
    return [Node(package='integrated_robot_vision', executable='object_detector', output='screen',
                 parameters=[shared, {'backend': backend, 'weights_path': weights,
                                      'processing_delay_s': delay, 'max_rate_hz': rate}]),
            Node(package='integrated_robot_vision', executable='vision_processor', output='screen',
                 parameters=[shared])]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('detector_backend', default_value='yolo'),
        DeclareLaunchArgument('weights_path', default_value=''),
        DeclareLaunchArgument('processing_delay_s', default_value='0'),
        DeclareLaunchArgument('max_rate_hz', default_value='10'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('trace_enabled', default_value='false'),
        DeclareLaunchArgument('trace_run_id', default_value=''),
        OpaqueFunction(function=launch_nodes)])
