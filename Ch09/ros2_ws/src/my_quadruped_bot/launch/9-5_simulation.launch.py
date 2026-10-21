import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import Command, LaunchConfiguration

def generate_launch_description():
    # 1. 패키지 경로 찾기
    pkg_name = 'my_quadruped_bot'
    pkg_share = get_package_share_directory(pkg_name)
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')

    # 2. 파일 경로 설정
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')
    world_file = os.path.join(pkg_share, 'worlds', 'empty_world.sdf')
    bridge_config = os.path.join(pkg_share, 'config', 'ros_gz_bridge.yaml')
    
    # 3. 런치 인자(Argument) 정의 및 구성
    # DeclareLaunchArgument를 등록해야 ros2 launch 명령어에서 인자 인식이 가능해집니다.
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )
    use_sim_time = LaunchConfiguration('use_sim_time')
    
    # 4. Gazebo 시뮬레이터 실행 설정
    # -r: 실행 즉시 시뮬레이션 시작 (Run), -v 4: 상세 로그 출력
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r -v 4 {world_file}'}.items(),
    )
    
    # 5. Robot State Publisher 설정
    # Xacro 명령어를 실행하여 XML 문자열을 실시간으로 파싱
    robot_desc_content = Command(['xacro ', xacro_file])
    
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc_content,
            'use_sim_time': use_sim_time
        }]
    )
    
    # 6. 로봇 스폰 (Spawn)
    # Gazebo의 'create' 가상 서비스를 호출하여 지정된 좌표에 로봇 소환
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',         # RSP가 발행한 토픽에서 모델 정보 참조
            '-name', 'my_quadruped',               # Gazebo 월드 내 객체 이름 지정
            '-x', '0.0', '-y', '0.0', '-z', '0.5', # 생성 위치 (바닥 충돌 방지를 위해 공중 배치)
            '-R', '0.0', '-P', '0.0', '-Y', '0.0'  # 초기 자세 (Roll, Pitch, Yaw)
        ],
        output='screen'
    )

    # 7. ROS-Gz Bridge 설정
    # 외부 YAML 설정 파일을 기반으로 ROS 2 <-> Gazebo 간 데이터 파이프라인 형성
    node_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_config}],
        output='screen'
    )

    # 8. 최종 실행 태스크 리스트 반환
    return LaunchDescription([
        declare_use_sim_time,
        gazebo,
        node_robot_state_publisher,
        spawn_entity,
        node_bridge,
    ])