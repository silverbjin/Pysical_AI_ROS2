"""Exclusive STAND/carry/crawl owners; no legacy locomotion or manipulation."""
import json
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from integrated_robot_navigation.carry_profile import CarryProfile, _validate_limits, swept_footprint
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.scene import load_scene


def launch_nodes(context):
    engine = LaunchConfiguration('engine').perform(context)
    directory = LaunchConfiguration('navigation_scene').perform(context)
    profile_path = LaunchConfiguration('carry_profile').perform(context)
    raw_validation = LaunchConfiguration('validation_mode').perform(context).lower()
    if raw_validation not in ('true', 'false'):
        raise ValueError('validation_mode must be true or false')
    record = load_scene(engine, directory)
    model = compile_model(Path(record['robot']['path']).read_text())
    profile = CarryProfile(**json.loads(Path(profile_path).read_text()))
    _validate_limits(profile.limits)
    swept_footprint(model, profile, profile.limits)
    share = Path(get_package_share_directory('integrated_robot_navigation'))
    sensors = IncludeLaunchDescription(PythonLaunchDescriptionSource(str(share/'launch/navigation_sensors.launch.py')),
        launch_arguments=dict(engine=engine, navigation_scene=directory).items())
    common = dict(use_sim_time=True, model_file=record['robot']['path'], carry_profile=profile_path,
                  engine=engine, validation_mode=raw_validation == 'true')
    nodes = [Node(package='integrated_robot_navigation', executable=name,
                  parameters=[common if name in ('motion_guard', 'crawl_controller', 'carry_manager', 'crawl_startup')
                              else {'use_sim_time': True}], output='screen')
             for name in ('motion_guard', 'crawl_controller', 'carry_manager', 'nav_projection', 'crawl_startup')]
    provenance = LaunchConfiguration('tf_provenance_output', default='').perform(context)
    if provenance:
        nodes.append(Node(package='integrated_robot_navigation_sensors', executable='tf_provenance',
                          arguments=[provenance], parameters=[{'use_sim_time': True}], output='screen'))
    return [sensors, *nodes]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('engine', default_value='mujoco'),
        DeclareLaunchArgument('navigation_scene'), DeclareLaunchArgument('carry_profile'),
        DeclareLaunchArgument('validation_mode', default_value='false'),
        DeclareLaunchArgument('tf_provenance_output', default_value=''),
        OpaqueFunction(function=launch_nodes)])
