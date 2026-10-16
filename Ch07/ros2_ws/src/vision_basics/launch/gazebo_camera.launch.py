import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    # 1. 패키지 경로 및 설정 변수
    pkg_name = 'vision_basics'  # 독자의 실습 환경에 따라 패키지명이 다를 수 있음을 본문에 명시해야 합니다.
    pkg_share = get_package_share_directory(pkg_name)   
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    
    xacro_file = os.path.join(pkg_share, 'urdf', 'my_robot.ros2_camera_gazebo.urdf.xacro')
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
    
    # 4. 가상 관절 값을 발행할 GUI 노드 추가
    # ⭐ [핵심 수정] ros2_control 대신 가상 관절 값을 발행할 GUI 노드 추가
    # 이 노드가 /joint_states 토픽을 발행하여 RSP에게 전달하고, TF 단절을 해결합니다.
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen'
    )
    
    # 5. Gazebo Simulator 실행
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items(),
    )

    # 6. 로봇 스폰 (Spawn) 노드
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description', 
            '-name', 'my_robot',
            # '-z', '0.5' 
        ],
        output='screen'
    )

    # 7-1. ROS-Gazebo 파라미터 브리지
    # Gazebo의 joint_state 매핑 인자([/world/.../joint_state)를 과감히 삭제했습니다.
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            
            # 2D camera의 경우, Gazebo에서 RGB 이미지와 카메라 정보(Intrinsic)가 하나의 토픽으로 나오는 경우가 많아 두 가지 메시지를 모두 브리지로 연결합니다.
            # 이미지 데이터 브리지
            # '/camera/image_raw@sensor_msgs/msg/Image@gz.msgs.Image',
            # 카메라 정보(Intrinsic) 브리지
            # '/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo',
            
            # depth camera의 경우, Gazebo에서 RGB와 Depth가 분리된 토픽으로 나오는 경우가 많아 두 토픽 모두 브리지로 연결합니다.
            "/camera/image@sensor_msgs/msg/Image@gz.msgs.Image",
            "/camera/depth_image@sensor_msgs/msg/Image@gz.msgs.Image",
            "/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
            "/camera/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked",
            
            # GUI의 제어 명령을 Gazebo 플러그인으로 전달하기 위한 브리지 추가 (ROS -> Gz 단방향)
            # ROS 2(Float64) 메시지를 Gazebo(Double)로 단방향 전달(]) 하겠다는 선언입니다.
            # 7개 모든 관절에 대한 단방향(ROS 2 -> Gazebo) 통신 채널 개설
            '/model/my_robot/joint1/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/my_robot/joint2/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/my_robot/joint3/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/my_robot/joint4/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/my_robot/joint_wrist/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/my_robot/joint_finger1/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double',
            '/model/my_robot/joint_finger2/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double' 
        ],
        remappings=[
            # "gazebo topic name", "ROS topic name" 쌍으로 나열
            ("/camera/image", "/camera/image_raw"),
            ("/camera/depth_image", "/camera/depth/image_raw"),
            ("/camera/points", "/camera/depth/points"),
            ("/camera/camera_info", "/camera/camera_info"),
            # ('/world/empty/model/my_robot/joint_state', '/joint_states'),
        ],        
        output='screen'
    )
    
    # 7-2. ⭐ [핵심 추가] 토픽 분할 중계 노드 (Inline Python Executable)
    # 별도 소스파일 등록 없이 실행을 가능하게 해주는 런치 내부 전용 스크립트 노드입니다.
    # /joint_states 배열에서 관절각을 뽑아 개별 /cmd_pos 토픽으로 가공 후 브리지로 쏩니다.
    # joint_splitter_node = Node(
    #     package='topic_tools',
    #     executable='relay',
    #     name='joint_splitter_bridge',
    #     output='screen',
    #     # 패키지 빌드 없이 파이썬 인터프리터로 즉석 구동하는 방식 구현
    #     executable='python3',
    #     arguments=['-c', 
    #         "import rclpy; "
    #         "from rclpy.node import Node; "
    #         "from sensor_msgs.msg import JointState; "
    #         "from std_msgs.msg import Float64; "
    #         "class Splitter(Node): "
    #         "    def __init__(self): "
    #         "        super().__init__('joint_splitter'); "
    #         "        self.sub = self.create_subscription(JointState, '/joint_states', self.cb, 10); "
    #         "        self.joints = ['joint1', 'joint2', 'joint3', 'joint4', 'joint_wrist', 'joint_finger1', 'joint_finger2']; "
    #         "        self.pubs = {n: self.create_publisher(Float64, f'/model/my_robot/{n}/cmd_pos', 10) for n in self.joints}; "
    #         "    def cb(self, msg): "
    #         "        for name, pos in zip(msg.name, msg.position): "
    #         "            if name in self.pubs: "
    #         "                m = Float64(); m.data = pos; self.pubs[name].publish(m); "
    #         "rclpy.init(); rclpy.spin(Splitter()); rclpy.shutdown();"
    #     ]
    # )
    
    # 7-2. ⭐ [핵심 추가] 토픽 분할 중계 노드 (표준 패키지 노드 실행 방식)
    # 패키지에 등록된 'joint_splitter' 진입점을 호출하여 깔끔하게 실행합니다.
    joint_splitter_node = Node(
        package='vision_basics',      # 패키지 이름
        executable='joint_splitter',         # setup.py에 등록한 entry_point 이름
        name='joint_splitter_node',          # 노드 실행 이름 (자유롭게 지정 가능)
        parameters=[{'use_sim_time': use_sim_time}], # 시뮬레이션 시간 동기화 유지
        output='screen'
    )

    # 8. ROS-Gazebo 이미지 전용 브리지
    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=['/camera/image_raw'],
        output='screen'
    )

    # 9. RViz2 실행
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}], 
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'),
        
        robot_state_publisher,
        joint_state_publisher_gui,  # 가상 조인트 제어기 배치
        gazebo,
        spawn_entity, 
        bridge,
        joint_splitter_node,  # 중계 노드 배치
        image_bridge,  
        rviz
    ])