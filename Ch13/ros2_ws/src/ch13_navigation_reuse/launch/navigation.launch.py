from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,ExecuteProcess,SetEnvironmentVariable,RegisterEventHandler,EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration,PythonExpression
from launch.conditions import IfCondition
from launch_ros.actions import Node
from ament_index_python.packages import get_package_prefix,get_package_share_directory

def generate_launch_description():
 python=LaunchConfiguration('python');repo=LaunchConfiguration('repo_root');report=LaunchConfiguration('report');scene=LaunchConfiguration('scene');limit=LaunchConfiguration('max_sim_s')
 share=Path(get_package_share_directory('ch13_navigation_reuse'));params=str(share/'config/nav2_params.yaml');bt=str(share/'config/navigate_no_recovery.xml')
 platform=ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.platform_adapter','--repo-root',repo,'--report',report,'--scene',scene,'--max-sim-s',limit],output='screen')
 actions=[DeclareLaunchArgument('python',default_value='/home/jinho/ch13_reuse_iit_d010212_venv/bin/python'),DeclareLaunchArgument('repo_root'),DeclareLaunchArgument('report'),DeclareLaunchArgument('scene',default_value='free'),DeclareLaunchArgument('max_sim_s',default_value='120'),SetEnvironmentVariable('ROS_LOCALHOST_ONLY','1'),SetEnvironmentVariable('ROS_DOMAIN_ID','135'),SetEnvironmentVariable('MUJOCO_GL','egl'),SetEnvironmentVariable('LP_NUM_THREADS','2'),RegisterEventHandler(OnProcessExit(target_action=platform,on_exit=[EmitEvent(event=Shutdown(reason='owned engine exited'))])),ExecuteProcess(cmd=[get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress'],output='screen')]
 for module,args in [('command_gateway',[]),('navigation_boundary',[]),('world_map',['--scene',scene])]:actions.append(ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.'+module]+args,output='screen'))
 actions.append(ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.vision_approach','--report',report],condition=IfCondition(PythonExpression(["'",scene,"' == 'vision'"])),output='screen'))
 actions.append(platform)
 for package,executable,name,remaps,extra in [
  ('nav2_planner','planner_server','planner_server',[],{}),
  ('nav2_controller','controller_server','controller_server',[('cmd_vel','/ch13/reuse/nav_cmd')],{}),
  ('nav2_velocity_smoother','velocity_smoother','velocity_smoother',[('cmd_vel','/ch13/reuse/nav_cmd'),('cmd_vel_smoothed','/ch13/reuse/smoothed_cmd')],{}),
  ('nav2_bt_navigator','bt_navigator','bt_navigator',[],{'default_nav_to_pose_bt_xml':bt})]:
  actions.append(Node(package=package,executable=executable,name=name,parameters=[params,extra],remappings=remaps,output='screen'))
 actions.append(Node(package='nav2_lifecycle_manager',executable='lifecycle_manager',name='reuse_lifecycle_manager',parameters=[{'use_sim_time':True,'autostart':True,'bond_timeout':10.,'node_names':['planner_server','controller_server','velocity_smoother','bt_navigator']}],output='screen'))
 return LaunchDescription(actions)
