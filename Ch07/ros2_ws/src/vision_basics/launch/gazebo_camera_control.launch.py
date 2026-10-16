import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    # 1. 패키지 경로 및 설정 변수
    pkg_name = 'vision_basics'
    pkg_share = get_package_share_directory(pkg_name)   
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    
    # 지시하신 비전/컨트롤 통합 Xacro 파일 경로
    xacro_file = os.path.join(pkg_share, 'urdf', 'my_robot.ros2_camera_control_gazebo.urdf.xacro')
    
    # RViz 설정 파일 경로
    rviz_config_file = os.path.join(pkg_share, 'rviz', 'display.rviz')

    # 2. Launch Argument 설정
    use_sim_time = LaunchConfiguration('use_sim_time')
    
    # 3. Robot State Publisher (RSP) 실행
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time, 
            'robot_description': ParameterValue(Command(['xacro ', xacro_file]), value_type=str)
        }]
    )
    
    # 4. Gazebo Simulator 실행
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items(),
    )

    # 5. 로봇 스폰 (Spawn) 노드
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description', 
            '-name', 'my_robot',
            '-z', '0.5' 
        ],
        output='screen'
    )

    # 6. ROS-Gazebo 파라미터 브리지 (⭐ 수정됨: 조인트 매핑 삭제)
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            # 카메라 정보 (Intrinsic) 브리지
            '/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo',
            # # # 이미지 데이터 브리지
            # '/camera/image_raw@sensor_msgs/msg/Image@gz.msgs.Image',
            
        ],
        output='screen'
    )

    # 7. ROS-Gazebo 이미지 전용 브리지
    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=['/camera/image_raw'],
        output='screen'
    )

    # 8. RViz2 실행
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}], 
        output='screen'
    )

    # ================================================================= #
    # 9. ⭐ [핵심 추가] ros2_control 제어기 스폰 (Spawner) 노드들
    # ================================================================= #
    
    # 관절 상태 브로드캐스터 실행
    load_joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        # parameters=[{"use_sim_time": use_sim_time}],    # 추가: 시뮬레이션 시간 사용 설정
        output="screen",
    )

    # 로봇 팔 제어기 실행
    load_arm_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_group_controller", "--controller-manager", "/controller_manager"],
        # parameters=[{"use_sim_time": use_sim_time}],    # 추가: 시뮬레이션 시간 사용 설정
        output="screen",
    )

    # 그리퍼 제어기 실행
    load_gripper_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gripper_group_controller", "--controller-manager", "/controller_manager"],
        # parameters=[{"use_sim_time": use_sim_time}],    # 추가: 시뮬레이션 시간 사용 설정
        output="screen",
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'),
        
        robot_state_publisher,
        gazebo,
        spawn_entity, 
        bridge,
        image_bridge,  
        rviz,
        
        # 컨트롤러 스포너 노드 추가
        load_joint_state_broadcaster,
        load_arm_controller,
        load_gripper_controller
    ])