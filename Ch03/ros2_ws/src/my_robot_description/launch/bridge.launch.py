import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    # 패키지 경로 및 YAML 파일 경로 설정
    pkg_dir = get_package_share_directory('my_robot_description')
    bridge_config_file = os.path.join(pkg_dir, 'config', 'ros_gz_bridge.yaml')

    # ros_gz_bridge 노드 실행
    bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': bridge_config_file,
        }],
        output='screen'
    )

    return LaunchDescription([
        bridge_node
    ])
