import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node
# [해결책] 거대 XML(URDF) 문자열 파싱 오류를 방지하기 위한 클래스 임포트
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_name = 'my_robot_description'
    pkg_share = get_package_share_directory(pkg_name)
    
    xacro_file = os.path.join(pkg_share, 'urdf', 'two_dof_arm.urdf.xacro')
    bridge_config = os.path.join(pkg_share, 'config', 'ros_gz_bridge.yaml')
    world_file = os.path.join(pkg_share, 'worlds', 'my_world.sdf')

    # 1. 로봇 모델 처리 (Xacro -> URDF 변환)
    # robot_desc = Command(['xacro ', xacro_file])
    # [수정] Command 출력을 명시적으로 string 타입의 ParameterValue로 감쌉니다.
    robot_desc = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)


    # 2. Robot State Publisher 실행
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': True}]
    )

    # 3. Gazebo Sim 실행 (-r 옵션으로 즉시 시작)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': ['-r ', world_file]}.items(),
    )

    # 4. 로봇 스폰 (Topic 방식 사용)
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'my_robot', '-topic', 'robot_description', 
                   '-x', '0.0', '-y', '0.0', '-z', '0.1'],
        output='screen'
    )

    # 5. ROS-Gazebo Bridge 실행
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['--ros-args', '-p', f'config_file:={bridge_config}'],
        output='screen'
    )

    return LaunchDescription([
        robot_state_publisher,
        gazebo,
        spawn_entity,
        ros_gz_bridge
    ])
