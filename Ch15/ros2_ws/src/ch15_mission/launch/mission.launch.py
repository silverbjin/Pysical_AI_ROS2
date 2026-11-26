from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
def setup(context):
    if LaunchConfiguration('profile').perform(context)!='mock':raise RuntimeError('G02 mock only; native physical runner is separate')
    if LaunchConfiguration('auto_start').perform(context).lower()!='false':raise RuntimeError('G02 no mission executor; auto_start forbidden')
    return [Node(package=p,executable=e,output='screen') for p,e in [('ch15_adapters','mock_servers'),('ch15_safety','sensor_watchdog'),('ch15_safety','command_arbiter'),('ch15_safety','readiness_monitor')]]
def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('profile',default_value='mock'),DeclareLaunchArgument('auto_start',default_value='false'),OpaqueFunction(function=setup)])
