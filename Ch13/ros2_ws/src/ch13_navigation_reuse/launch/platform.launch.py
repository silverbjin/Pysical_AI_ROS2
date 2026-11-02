import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,ExecuteProcess,SetEnvironmentVariable,RegisterEventHandler,EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_prefix


def generate_launch_description():
    python=LaunchConfiguration('python');repo=LaunchConfiguration('repo_root');report=LaunchConfiguration('report')
    platform=ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.platform_adapter','--repo-root',repo,'--report',report],output='screen')
    return LaunchDescription([
        DeclareLaunchArgument('python',default_value=os.environ.get('CH13_REUSE_VENV','/home/jinho/ch13_reuse_iit_d010212_venv')+'/bin/python'),
        DeclareLaunchArgument('repo_root'),DeclareLaunchArgument('report'),
        SetEnvironmentVariable('ROS_LOCALHOST_ONLY','1'),SetEnvironmentVariable('ROS_DOMAIN_ID','135'),
        RegisterEventHandler(OnProcessExit(target_action=platform,on_exit=[EmitEvent(event=Shutdown(reason='owned platform exited'))])),
        ExecuteProcess(cmd=[get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress'],output='screen'),
        ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.command_gateway'],output='screen'),
        platform,
    ])
