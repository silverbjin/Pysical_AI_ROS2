"""Exactly one native engine, existing control ownership, and real RGB-D vision."""
from pathlib import Path
import math

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_nodes(context):
    values = {key: LaunchConfiguration(key).perform(context) for key in (
        'engine', 'detector_backend', 'weights_path', 'tracking_enabled',
        'processing_delay_s', 'use_sim_time', 'world', 'model_path', 'allow_camera_motion_test')}
    if values['engine'] not in ('gazebo', 'mujoco'):
        raise ValueError('select exactly one engine: gazebo or mujoco')
    if values['use_sim_time'].lower() != 'true':
        raise ValueError('native engine system requires use_sim_time=true')
    if values['tracking_enabled'].lower() not in ('true', 'false'):
        raise ValueError('tracking_enabled must be an explicit boolean')
    if values['allow_camera_motion_test'].lower() not in ('true', 'false'):
        raise ValueError('allow_camera_motion_test must be an explicit boolean')
    if values['detector_backend'] not in ('yolo', 'color_fixture'):
        raise ValueError('explicit supported detector backend required')
    if (values['detector_backend'] == 'yolo' and
            (not Path(values['weights_path']).is_absolute() or not Path(values['weights_path']).is_file())):
        raise ValueError('existing absolute local YOLO weights required before starting engine')
    delay = float(values['processing_delay_s'])
    if not math.isfinite(delay) or delay < 0:
        raise ValueError('finite nonnegative inference delay required')

    def include(package, filename, arguments):
        path = Path(get_package_share_directory(package))/'launch'/filename
        return IncludeLaunchDescription(PythonLaunchDescriptionSource(str(path)),
                                        launch_arguments=arguments.items())

    engine_arguments = {'vision_enabled': 'true'}
    if values['engine'] == 'mujoco':
        headless = LaunchConfiguration('mujoco_headless', default='true').perform(context).lower()
        if headless not in ('true', 'false'):
            raise ValueError('mujoco_headless must be an explicit boolean')
        engine_arguments['mujoco_headless'] = headless
    override = 'world' if values['engine'] == 'gazebo' else 'model_path'
    if values[override]:
        engine_arguments[override] = values[override]
    actions = [include('integrated_robot_description', values['engine']+'.launch.py', engine_arguments),
               include('integrated_robot_runtime', 'architecture.launch.py',
                       {'use_sim_time': 'true', 'include_demo_vision': 'false',
                        'wait_for_controllers': 'true',
                        'allow_camera_motion_test': values['allow_camera_motion_test']}),
               include('integrated_robot_vision', 'vision.launch.py',
                       {k: values[k] for k in ('detector_backend', 'weights_path',
                                              'processing_delay_s', 'use_sim_time')})]
    if values['tracking_enabled'].lower() == 'true':
        actions.append(Node(package='integrated_robot_runtime', executable='tracking_requester',
                            output='screen', parameters=[{'use_sim_time': True}]))
    return actions


def generate_launch_description():
    defaults = dict(engine='mujoco', detector_backend='yolo', weights_path='',
                    tracking_enabled='false', processing_delay_s='0', use_sim_time='true',
                    world='', model_path='', allow_camera_motion_test='false', mujoco_headless='true')
    return LaunchDescription([*[DeclareLaunchArgument(k, default_value=v) for k, v in defaults.items()],
                              OpaqueFunction(function=launch_nodes)])
