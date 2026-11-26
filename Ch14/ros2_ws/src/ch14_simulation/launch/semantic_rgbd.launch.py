from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,ExecuteProcess,SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from pathlib import Path

def generate_launch_description():
    world=str(Path(get_package_share_directory('ch14_simulation'))/'worlds/semantic_rgbd.sdf')
    return LaunchDescription([
        DeclareLaunchArgument('assets',description='absolute directory created by pinned asset fetcher'),
        DeclareLaunchArgument('onnx',description='absolute verified ONNX file'),
        DeclareLaunchArgument('model_sha256',description='verified ONNX SHA256'),
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH',LaunchConfiguration('assets')),
        ExecuteProcess(cmd=['gz','sim','-s','-r','--headless-rendering',world],output='screen'),
        Node(package='ros_gz_bridge',executable='parameter_bridge',arguments=[
          '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
          '/ch14/rgbd/image@sensor_msgs/msg/Image[gz.msgs.Image',
          '/ch14/rgbd/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
          '/ch14/rgbd/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo'],
          remappings=[('/ch14/rgbd/image','/camera/color/image_raw'),('/ch14/rgbd/depth_image','/camera/aligned_depth_to_color/image_raw'),('/ch14/rgbd/camera_info','/camera/color/camera_info')],
          parameters=[{'override_frame_id':'camera_optical'}],output='screen'),
        Node(package='tf2_ros',executable='static_transform_publisher',arguments=['--x','0','--y','0','--z','1','--roll','-1.5707963267948966','--pitch','0','--yaw','-1.5707963267948966','--frame-id','odom','--child-frame-id','camera_optical']),
        Node(package='ch14_ai_perception',executable='detector_node',parameters=[{'onnx':ParameterValue(LaunchConfiguration('onnx'),value_type=str),
          'model_sha256':ParameterValue(LaunchConfiguration('model_sha256'),value_type=str),'rgbd':True,'use_sim_time':True,'target_class':'person','target_frame':'odom','trace_inputs':True}],output='screen')])
