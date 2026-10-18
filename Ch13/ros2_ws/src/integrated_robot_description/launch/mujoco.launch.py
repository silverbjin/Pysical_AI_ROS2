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
from launch.actions import TimerAction
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def materialize_controller_config(source):
    """Avoid ros2_control treating a package path as a robot_description argument."""
    data = Path(source).read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:12]
    target = Path(tempfile.gettempdir()) / f'ch13_2_controllers_{digest}.yaml'
    if not target.exists() or target.read_bytes() != data:
        temporary = target.with_suffix('.tmp')
        temporary.write_bytes(data)
        temporary.replace(target)
    return str(target)


def generate_launch_description():
    share = get_package_share_directory('integrated_robot_description')
    xacro_path = os.path.join(share, 'urdf', 'robot_system.urdf.xacro')
    model_path = os.path.join(share, 'mujoco', 'robot_system.xml')
    controllers = materialize_controller_config(
        os.path.join(share, 'config', 'controllers.yaml')
    )
    description = ParameterValue(
        Command(
            ['xacro ', xacro_path, ' control_backend:=mujoco mujoco_model_path:=', model_path]
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
    return LaunchDescription(
        [control_node, state_publisher, TimerAction(period=3.0, actions=spawners)]
    )
