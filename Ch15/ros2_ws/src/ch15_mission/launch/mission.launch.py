from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
def setup(context):
    if LaunchConfiguration('profile').perform(context)!='mock':raise RuntimeError('native physical runner is separate; physical_full BLOCKED')
    auto=LaunchConfiguration('auto_start').perform(context).lower()
    if auto not in ('true','false'):raise RuntimeError('invalid auto_start')
    return [Node(package='ch15_adapters',executable='mock_servers',output='screen'),
            Node(package='ch15_safety',executable='sensor_watchdog',output='screen'),
            Node(package='ch15_safety',executable='command_arbiter',parameters=[{'require_mission_authorization':True}],output='screen'),
            Node(package='ch15_safety',executable='readiness_monitor',output='screen'),
            Node(package='ch15_mission',executable='mission_executor',parameters=[{'auto_start':auto=='true','evidence_dir':LaunchConfiguration('evidence_dir').perform(context)}],output='screen')]
def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('profile',default_value='mock'),DeclareLaunchArgument('auto_start',default_value='false'),DeclareLaunchArgument('evidence_dir',default_value=''),OpaqueFunction(function=setup)])
