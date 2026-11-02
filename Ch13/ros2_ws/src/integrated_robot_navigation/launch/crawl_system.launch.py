"""Exclusive STAND/carry/crawl owners; no legacy locomotion or manipulation."""
import json
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from integrated_robot_navigation.carry_profile import CarryProfile, _validate_limits, swept_footprint,validate_profile
from integrated_robot_navigation.execution_contract import g2_execution_profile
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.scene import load_scene


def launch_nodes(context):
    engine = LaunchConfiguration('engine').perform(context)
    directory = LaunchConfiguration('navigation_scene').perform(context)
    profile_path = LaunchConfiguration('carry_profile').perform(context)
    raw_validation = LaunchConfiguration('validation_mode').perform(context).lower()
    if raw_validation not in ('true', 'false'):
        raise ValueError('validation_mode must be true or false')
    raw_g2=LaunchConfiguration('g2_validation_mode',default='false').perform(context).lower()
    if raw_g2 not in ('true','false') or raw_g2=='true' and raw_validation!='true':
        raise ValueError('G2 requires explicit validation_mode')
    clock_mode = LaunchConfiguration('control_clock_mode', default='native').perform(context)
    if clock_mode not in ('native', 'relay100'):
        raise ValueError('control_clock_mode must be native or relay100')
    if clock_mode == 'relay100' and raw_validation != 'true':
        raise ValueError('control_clock relay experiment requires validation_mode; no CRAWL admission')
    record = load_scene(engine, directory)
    if record.get('position_reference_mode','native')!='native' and raw_validation!='true':
        raise ValueError('reference experiment requires validation_mode; no CRAWL admission')
    model = compile_model(Path(record['robot']['path']).read_text())
    profile = CarryProfile(**json.loads(Path(profile_path).read_text()))
    _validate_limits(profile.limits)
    swept_footprint(model, profile, profile.limits)
    g2_parameters={}
    if raw_g2=='true':
        execution=g2_execution_profile(record,clock_mode)
        accepted,reason=validate_profile(profile,model,engine,execution_profile=execution)
        if not accepted:raise ValueError('G2 native profile rejected: '+reason)
        g2_parameters=dict(g2_validation_mode=True,native_execution_profile=json.dumps(execution,sort_keys=True))
    share = Path(get_package_share_directory('integrated_robot_navigation'))
    sensors = IncludeLaunchDescription(PythonLaunchDescriptionSource(str(share/'launch/navigation_sensors.launch.py')),
        launch_arguments=dict(engine=engine, navigation_scene=directory).items())
    common = dict(use_sim_time=True, model_file=record['robot']['path'], carry_profile=profile_path,
                  engine=engine, validation_mode=raw_validation == 'true')
    nodes = [Node(package='integrated_robot_navigation', executable=name,
                  parameters=[dict(common,control_clock_mode=clock_mode,**g2_parameters) if name=='crawl_controller' else
                              dict(common,**g2_parameters) if name=='motion_guard' else
                              dict(common, control_clock_mode=clock_mode) if name=='crawl_startup' else
                              common if name in ('motion_guard', 'crawl_controller', 'carry_manager')
                              else {'use_sim_time': True}], output='screen',
                  remappings=[('/clock', '/navigation/control_clock')] if clock_mode == 'relay100' else [])
             for name in ('motion_guard', 'crawl_controller', 'carry_manager', 'nav_projection', 'crawl_startup')]
    if clock_mode == 'relay100':
        trace = LaunchConfiguration('control_clock_output', default='').perform(context)
        nodes.append(Node(package='integrated_robot_navigation_sensors', executable='control_clock_relay',
                          arguments=[trace] if trace else [],
                          parameters=[{'use_sim_time': False}], output='screen'))
    provenance = LaunchConfiguration('tf_provenance_output', default='').perform(context)
    if provenance:
        nodes.append(Node(package='integrated_robot_navigation_sensors', executable='tf_provenance',
                          arguments=[provenance], parameters=[{'use_sim_time': True}], output='screen'))
    return [sensors, *nodes]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('engine', default_value='mujoco'),
        DeclareLaunchArgument('navigation_scene'), DeclareLaunchArgument('carry_profile'),
        DeclareLaunchArgument('validation_mode', default_value='false'),
        DeclareLaunchArgument('g2_validation_mode',default_value='false'),
        DeclareLaunchArgument('control_clock_mode', default_value='native'),
        DeclareLaunchArgument('control_clock_output', default_value=''),
        DeclareLaunchArgument('tf_provenance_output', default_value=''),
        OpaqueFunction(function=launch_nodes)])
