import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
# [해결책] 거대 XML(URDF) 문자열 파싱 오류를 방지하기 위한 클래스 임포트
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    # 1. 패키지 및 URDF 파일 경로 설정
    pkg_share = get_package_share_directory('my_robot_description')
    
    # 3장에서 만든 xacro 파일 경로 (자신의 파일명에 맞게 수정)
    urdf_file = PathJoinSubstitution([pkg_share, 'urdf', LaunchConfiguration('model')])
    
    # 2. Xacro를 URDF로 변환하는 커맨드 생성
    # Command 함수는 실행 시점에 xacro 명령어를 수행하여 XML 문자열을 얻어낸다.
    # robot_description_content = Command(['xacro ', urdf_file])
    robot_description_content = ParameterValue(Command(['xacro ', urdf_file]), value_type=str)

    # 3. Robot State Publisher 노드 설정
    # 이 노드는 'robot_description' 파라미터로 URDF 내용을 필수로 받는다.
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_content}]
    )

    # 4. Joint State Publisher GUI 노드 설정
    # GUI 슬라이더를 통해 가짜 joint_states를 발행한다.
    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui'
    )
    
    # 5. 패키지 경로를 동적으로 획득
    package_name = 'my_robot_description'
    rviz_config_path = os.path.join(                # setup.py의 data_files 설정에 따라 'rviz/' 폴더 내의 파일을 찾습니다.
        get_package_share_directory(package_name),  # 패키지 공유 디렉토리 경로 확보
        'rviz',
        'display.rviz'
    )

    # 6. RViz2 노드 설정
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_path], # 지정된 설정 파일 로드
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument('model', default_value='two_dof_arm.urdf',
                              description='URDF or Xacro filename in the package urdf directory'),
        robot_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz_node
    ])
