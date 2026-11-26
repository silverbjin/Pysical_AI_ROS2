from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    args={'onnx':'','model_sha256':'','mode':'async','backend':'ort','rgbd':'false',
          'use_sim_time':'false','target_frame':'odom','target_class':'bus','threads':'2','delay_ms':'0.0'}
    params={k:ParameterValue(LaunchConfiguration(k),value_type=bool if k in ('rgbd','use_sim_time') else int if k=='threads' else float if k=='delay_ms' else str) for k in args}
    return LaunchDescription([*(DeclareLaunchArgument(k,default_value=v) for k,v in args.items()),
        Node(package='ch14_ai_perception',executable='detector_node',output='screen',parameters=[params])])
