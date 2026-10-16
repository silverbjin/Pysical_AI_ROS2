# 파일 생성: ~/ros2_ws/src/my_quadruped_bot/launch/localization.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 앞서 생성한 패키지명(my_quadruped_bot)과 일치시킵니다.
    pkg_share = get_package_share_directory('my_quadruped_bot')
    ekf_config_path = os.path.join(pkg_share, 'config', 'ekf.yaml')

    return LaunchDescription([
        # 1. 다리 오도메트리 발행 노드
        Node(
            package='my_quadruped_bot',
            executable='leg_odometry',
            name='leg_odometry',
            output='screen'
        ),
        
        # 2. Robot Localization (EKF) 노드
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[ekf_config_path],
            remappings=[('/odometry/filtered', '/odom')] # 최종 출력을 /odom으로 통일하여 RViz2 연동 편의성 확보
        )
    ])