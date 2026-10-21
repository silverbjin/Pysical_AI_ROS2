# [코드 9-15] launch/simulation.launch.py
import os
import xacro # [보완] Xacro 파일을 런타임에 직접 파싱하기 위해 필수 임포트
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # 패키지 이름 및 셰어(Share) 디렉터리 경로 설정
    pkg_name = 'my_quadruped_bot'
    pkg_share = get_package_share_directory(pkg_name)
 
    # 1. 월드(World) 파일 경로 설정 (앞서 만든 9.4.4절의 SDF 무대)
    world_file = os.path.join(pkg_share, 'worlds', 'empty_world.sdf')
    
    # 2. Gazebo Harmonic 실행 가동 (ros_gz_sim의 기본 런치 파일 포함)
    # '-r' 인자를 전달하여 시뮬레이터가 켜짐과 동시에 재생(Run)되도록 설정
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_file}'}.items(),
    )
 
    # 3. 로봇 모델(Xacro) 실시간 파싱 및 URDF 변환
    # [정석 구현] 미리 변환할 필요 없이, 런치 시스템이 켜지면서 자동으로 URDF 컴파일을 수행함
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')
    robot_description_raw = xacro.process_file(xacro_file).toxml()
 
    # 4. Robot State Publisher 노드 (로봇의 TF 링크 트리 상태 계산 및 /tf 발행)
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_raw,
                     'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )
 
    # 5. Gazebo 환경 내에 로봇 엔티티 생성 노드 (create)
    # 지면 바닥과 로봇 다리가 충돌하여 꼬이는 것을 방지하기 위해 Z축으로 0.5m 공중 스폰
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description', # robot_state_publisher가 쏘는 토픽 수신
            '-name', 'my_quadruped',       # 가제보 월드 내부에서 불릴 로봇 고유 이름
            '-z', '0.5'                    # 초기 스폰 높이 (미터 단위)
        ],
        output='screen'
    )
 
    # 6. ROS-Gazebo 전방향 통신 브리지 가동 (앞서 만든 9.4.5절의 YAML 매핑 적용)
    bridge_config = os.path.join(pkg_share, 'config', 'ros_gz_bridge.yaml')
    node_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_config}],
        output='screen'
    )
 
    # 정의된 모든 인프라 노드들을 런치 엔진에 반환하여 동시 구동
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        gazebo,
        node_robot_state_publisher,
        spawn_entity,
        node_bridge
    ])
