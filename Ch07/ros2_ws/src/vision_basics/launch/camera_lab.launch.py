"""Ch07 isolated camera simulation; verify actual Gazebo topics before accepting."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('vision_basics')
    sim = get_package_share_directory('ros_gz_sim')
    xacro_path = os.path.join(pkg, 'urdf', 'my_robot.urdf.xacro')
    world = os.path.join(pkg, 'worlds', 'ch07_camera_lab.sdf')
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': ParameterValue(
            Command(['xacro ', xacro_path]), value_type=str)}],
        output='screen',
    )
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': '-r -v 3 ' + world}.items(),
    )
    spawn = Node(
        package='ros_gz_sim', executable='create',
        arguments=['-topic', 'robot_description', '-name', 'ch07_robot', '-z', '0.12'],
        output='screen',
    )
    # Gazebo RGBD topic naming is engine/plugin dependent. Check `gz topic -l`
    # and remap bridge arguments to actual published topics if necessary.
    bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        arguments=[
            '/camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        parameters=[{'override_frame_id': 'camera_optical_frame'}],
        remappings=[
            ('/camera/image', '/camera/image_raw'),
            ('/camera/depth_image', '/camera/depth/image_raw'),
        ],
        output='screen',
    )
    return LaunchDescription([gazebo, rsp, spawn, bridge])
