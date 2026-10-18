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

"""Select one physical engine with its real eye-in-hand sensors enabled."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def select_engine(context):
    engine = LaunchConfiguration('engine').perform(context)
    if engine not in ('gazebo', 'mujoco'):
        raise ValueError('engine must be gazebo or mujoco')
    share = Path(get_package_share_directory('integrated_robot_description'))
    return [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(share / 'launch' / (engine + '.launch.py'))),
        launch_arguments={'vision_enabled': 'true'}.items())]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('engine', default_value='gazebo'),
                              OpaqueFunction(function=select_engine)])
