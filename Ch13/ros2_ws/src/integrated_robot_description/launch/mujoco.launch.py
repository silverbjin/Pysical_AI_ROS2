# Copyright 2026 Jinho
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import os
from pathlib import Path
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, TimerAction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def materialize_controller_config(source, plugin_source=None):
    """Avoid ros2_control treating a package path as a robot_description argument."""
    data = Path(source).read_bytes()
    if plugin_source is not None:
        # Controlled roots are disjoint: named controllers and /**.
        # One short file avoids native CM multi-file argv forwarding errors.
        data += b'\n' + Path(plugin_source).read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:12]
    target = Path(tempfile.gettempdir()) / f'ch13_2_controllers_{digest}.yaml'
    if not target.exists() or target.read_bytes() != data:
        temporary = target.with_suffix('.tmp')
        temporary.write_bytes(data)
        temporary.replace(target)
    return str(target)


def camera_plugin_config(share, vision):
    return str(Path(share)/'config'/(
        'mujoco_vision_plugins.yaml' if vision else 'mujoco_legacy_cameras.yaml'))


def launch_nodes(context):
    share = get_package_share_directory('integrated_robot_description')
    vision = LaunchConfiguration('vision_enabled').perform(context).lower() == 'true'
    xacro_path = os.path.join(share, 'urdf', 'robot_system.urdf.xacro')
    model_path = LaunchConfiguration('model_path').perform(context) or os.path.join(
        share, 'mujoco', 'vision_fixture.xml' if vision else 'robot_system.xml')
    controllers = materialize_controller_config(
        os.path.join(share, 'config', 'controllers.yaml'),
        camera_plugin_config(share, vision),
    )
    description = ParameterValue(
        Command(
            ['xacro ', xacro_path, ' control_backend:=mujoco mujoco_model_path:=', model_path,
             ' vision_enabled:=', str(vision).lower(),
             ' mujoco_headless:=', LaunchConfiguration('mujoco_headless').perform(context)]
        ),
        value_type=str,
    )
    control_node = Node(
        package='mujoco_ros2_control',
        executable='ros2_control_node',
        output='screen',
        parameters=[{'robot_description': description, 'use_sim_time': True}, controllers],
    )
    state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': description, 'use_sim_time': True}],
    )
    spawners = [
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=[name, '--param-file', controllers],
            output='screen',
        )
        for name in (
            'joint_state_broadcaster',
            'leg_position_controller',
            'arm_trajectory_controller',
            'gripper_position_controller',
        )
    ]
    nodes = [control_node, state_publisher, TimerAction(period=3.0, actions=spawners)]
    if vision:
        nodes.append(Node(package='integrated_robot_vision', executable='native_pose_adapter',
                          parameters=[{'engine': 'mujoco', 'use_sim_time': True}]))
        nodes.append(Node(package='integrated_robot_vision',
                          executable='native_camera_info_adapter',
                          parameters=[{'use_sim_time': True}]))
    return nodes


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('vision_enabled', default_value='false'),
                              DeclareLaunchArgument('mujoco_headless', default_value='false'),
                              DeclareLaunchArgument('model_path', default_value=''),
                              OpaqueFunction(function=launch_nodes)])
