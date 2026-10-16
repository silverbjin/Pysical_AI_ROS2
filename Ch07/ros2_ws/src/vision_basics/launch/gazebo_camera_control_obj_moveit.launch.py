import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import yaml  # 📌 추가된 부분
# 📌 SetParameter 임포트 추가
from launch_ros.actions import SetParameter

def generate_launch_description():
    # 1. 패키지 경로 및 설정 변수
    pkg_name = 'vision_basics'
    pkg_share = get_package_share_directory(pkg_name)  
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    
    # MoveIt 설정 패키지 경로 추가
    moveit_config_pkg = get_package_share_directory('my_robot_moveit_config')
    
    # 비전/컨트롤 통합 Xacro 파일 경로
    xacro_file = os.path.join(pkg_share, 'urdf', 'my_robot.ros2_camera_control_gazebo.urdf.xacro')
    
    # 큐브 객체용 SDF 파일 경로
    cube_sdf_file = os.path.join(pkg_share, 'models', 'test_box.sdf')
    
    # RViz 설정 파일 경로 (MoveIt Setup Assistant가 생성한 파일 사용)
    rviz_config_file = os.path.join(moveit_config_pkg, 'config', 'moveit.rviz')

    # 2. Launch Argument 설정
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    
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
        ],
        output='screen'
    )

    # 5-2. 테스트 큐브(물체) 스폰 노드
    spawn_cube = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-file', cube_sdf_file,
            '-name', 'test_box',
            '-x', '1.0',  
            '-z', '0.025' 
        ],
        output='screen'
    )

    # 6. ROS-Gazebo 파라미터 브리지
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo',
            "/camera/image@sensor_msgs/msg/Image@gz.msgs.Image",   
            # [추가됨] Depth 영상 브릿지 (Gazebo -> ROS)
            '/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',         
        ],
        remappings=[
            ("/camera/image", "/camera/image_raw"),
            # [추가됨] Gazebo 토픽을 ROS 2 타겟 토픽으로 리매핑
            ('/camera/depth_image', '/camera/depth/image_raw'),
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
    # 📌 FIX: RViz가 역기구학 연산을 수행하여 인터랙티브 마커를 띄울 수 있도록 kinematics.yaml 경로를 파라미터 배열에 직접 추가
    # 📌 FIX: yaml 파일을 파이썬 딕셔너리로 읽어들여서 파라미터로 전달
    kinematics_yaml_path = os.path.join(moveit_config_pkg, 'config', 'kinematics.yaml')
    with open(kinematics_yaml_path, 'r') as file:
        kinematics_dict = yaml.safe_load(file)
    
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[
            {'use_sim_time': use_sim_time},
            # os.path.join(moveit_config_pkg, 'config', 'kinematics.yaml')
            {'robot_description_kinematics': kinematics_dict}  # 📌 직접 파일 경로 대신 딕셔너리 주입
        ],
        output='screen'
    )

    # 9. ros2_control 제어기 스폰 노드들
    # 📌 FIX: --controller-manager 인자의 앞 슬래시(/) 제거 및 use_sim_time 파라미터 필수 추가
    load_joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "controller_manager"],
        parameters=[{'use_sim_time': use_sim_time}],
        output="screen",
    )

    # 📌 FIX: 컨트롤러 이름을 MoveIt 설정 규격인 'arm_group_controller'로 변경, 슬래시 제거, sim_time 추가
    load_arm_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_group_controller", "--controller-manager", "controller_manager"],
        parameters=[{'use_sim_time': use_sim_time}],
        output="screen",
    )

    # 📌 FIX: 슬래시 제거 및 use_sim_time 파라미터 추가
    load_gripper_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gripper_group_controller", "--controller-manager", "controller_manager"],
        parameters=[{'use_sim_time': use_sim_time}],
        output="screen",
    )

    # 10. MoveIt 2 실행 (move_group)
    move_group_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(moveit_config_pkg, 'launch', 'move_group.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(), # not work
    )
    
    return LaunchDescription([
        # ros2 param set /move_group use_sim_time true
        SetParameter(name='use_sim_time', value=True),
        
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'),
        
        robot_state_publisher,
        gazebo,
        spawn_entity,
        spawn_cube,
        bridge,
        image_bridge,  
        rviz,
        load_joint_state_broadcaster,
        load_arm_controller,
        load_gripper_controller,
        
        # MoveIt 노드 추가
        move_group_launch
    ])