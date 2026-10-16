from launch import LaunchDescription
from launch_ros.actions import Node
# 패키지 경로를 동적으로 획득하기 위한 유틸리티
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 패키지 경로를 동적으로 획득
    package_name = 'my_robot_tf'
    rviz_config_path = os.path.join(                # setup.py의 data_files 설정에 따라 'rviz/' 폴더 내의 파일을 찾습니다.
        get_package_share_directory(package_name),  # 패키지 공유 디렉토리 경로 확보
        'rviz',
        'multi_static_tf.rviz'
    )
    
    return LaunchDescription([
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments = ['0', '0', '1', '0', '0', '0', 'world', 'base_link']
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments = ['0.1', '0', '0.2', '0', '0', '0', 'base_link', 'lidar']
        ),
        # RViz2 노드 실행 추가
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_path], # 지정된 설정 파일 로드
            output='screen'
        ),
    ])
