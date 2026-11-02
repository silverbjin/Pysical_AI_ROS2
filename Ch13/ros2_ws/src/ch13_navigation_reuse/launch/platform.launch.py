from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,ExecuteProcess,SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_prefix

def generate_launch_description():
    python=LaunchConfiguration('python');repo=LaunchConfiguration('repo_root');report=LaunchConfiguration('report')
    return LaunchDescription([
        DeclareLaunchArgument('python',default_value='/home/jinho/ch13_reuse_iit_d010212_venv/bin/python'),
        DeclareLaunchArgument('repo_root'),DeclareLaunchArgument('report'),
        SetEnvironmentVariable('ROS_LOCALHOST_ONLY','1'),SetEnvironmentVariable('ROS_DOMAIN_ID','135'),
        ExecuteProcess(cmd=[get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress'],output='screen'),
        ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.command_gateway'],output='screen'),
        ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.platform_adapter','--repo-root',repo,'--report',report],output='screen'),
    ])
