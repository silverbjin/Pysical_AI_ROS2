import os
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,ExecuteProcess,SetEnvironmentVariable,RegisterEventHandler,EmitEvent,OpaqueFunction
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration,PythonExpression
from launch.conditions import IfCondition
from launch_ros.actions import Node
from ament_index_python.packages import get_package_prefix,get_package_share_directory

def planning_parameters():
 from ch13_piper_moveit_config.configuration import parameters
 config=parameters()
 if (os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1'
     and os.environ.get('CH13_VALIDATION_SCENARIO')=='level3_house'):
  # TOTG blends can leave a collision-free geometric path near table legs.
  # Keep ValidateSolution authoritative after the tighter joint-space blend.
  config['ompl']['path_tolerance']=.001
 return config

def generate_launch_description():
 python=LaunchConfiguration('python');repo=LaunchConfiguration('repo_root');report=LaunchConfiguration('report');scene=LaunchConfiguration('scene');limit=LaunchConfiguration('max_sim_s')
 share=Path(get_package_share_directory('ch13_navigation_reuse'));params=str(share/'config/nav2_params.yaml');bt=str(share/'config/navigate_no_recovery.xml')
 manipulation=LaunchConfiguration('manipulation')
 platform=ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.platform_adapter','--repo-root',repo,'--report',report,'--scene',scene,'--max-sim-s',limit,'--manipulation',manipulation,'--pick-scene',LaunchConfiguration('pick_scene')],output='screen')
 actions=[DeclareLaunchArgument('python',default_value=os.environ.get('CH13_REUSE_VENV','/home/jinho/ch13_reuse_iit_d010212_venv')+'/bin/python'),DeclareLaunchArgument('repo_root'),DeclareLaunchArgument('report'),DeclareLaunchArgument('scene',default_value='free'),DeclareLaunchArgument('max_sim_s',default_value='120'),DeclareLaunchArgument('vision_inference_hz',default_value='10'),DeclareLaunchArgument('manipulation',default_value='false',choices=['true','false']),DeclareLaunchArgument('pick_scene',default_value='false',choices=['true','false']),DeclareLaunchArgument('planning',default_value='false',choices=['true','false']),SetEnvironmentVariable('ROS_LOCALHOST_ONLY','1'),SetEnvironmentVariable('ROS_DOMAIN_ID','135'),SetEnvironmentVariable('MUJOCO_GL','egl'),SetEnvironmentVariable('LP_NUM_THREADS','2'),RegisterEventHandler(OnProcessExit(target_action=platform,on_exit=[EmitEvent(event=Shutdown(reason='owned engine exited'))])),ExecuteProcess(cmd=[get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress',PythonExpression(["'--manipulation' if '",manipulation,"' == 'true' else '--navigation-only'"])],output='screen')]
 for module,args in [('command_gateway',['--manipulation',manipulation]),('navigation_boundary',[]),('world_map',['--scene',scene,'--report',report])]:actions.append(ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.'+module]+args,output='screen'))
 def planner(context):
  return [Node(package='ch13_manipulation_planner',executable='planner_runtime',name='reuse_move_group',
               parameters=[planning_parameters()],remappings=[('joint_states','/ch13/reuse/joint_states')],output='screen')]
 actions.append(OpaqueFunction(function=planner,condition=IfCondition(LaunchConfiguration('planning'))))
 actions.append(ExecuteProcess(cmd=[python,'-m','ch13_navigation_reuse.vision_approach','--report',report,'--inference-hz',LaunchConfiguration('vision_inference_hz'),'--latest-camera',manipulation,'--target-shape',PythonExpression(["'cylinder' if '",LaunchConfiguration('pick_scene'),"' == 'true' else 'fixture'"])],condition=IfCondition(PythonExpression(["'",scene,"' == 'vision'"])),output='screen'))
 actions.append(platform)
 for package,executable,name,remaps,extra in [
  ('nav2_planner','planner_server','planner_server',[],{}),
  ('nav2_controller','controller_server','controller_server',[('cmd_vel','/ch13/reuse/nav_cmd')],{}),
  ('nav2_velocity_smoother','velocity_smoother','velocity_smoother',[('cmd_vel','/ch13/reuse/nav_cmd'),('cmd_vel_smoothed','/ch13/reuse/smoothed_cmd')],{}),
  ('nav2_bt_navigator','bt_navigator','bt_navigator',[],{'default_nav_to_pose_bt_xml':bt})]:
  node_params=params
  if (name=='controller_server' and os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1'
      and os.environ.get('CH13_VALIDATION_SCENARIO') in ('level1_floor','level2_obstacles','level3_house')):
   from nav2_common.launch import RewrittenYaml
   from launch_ros.descriptions import ParameterFile
   rewrites={'controller_server.ros__parameters.goal_checker.xy_goal_tolerance':'0.015'}
   if (os.environ.get('CH13_VALIDATION_SCENARIO') in ('level2_obstacles','level3_house')
       and os.environ.get('CH13_EXPERIMENTAL_SE2')=='1'):
    # Keep checking XY while turning: the first tolerance crossing is not arrival.
    rewrites['controller_server.ros__parameters.goal_checker.stateful']='false'
    # RPP has its own XY latch; both must keep correcting position.
    rewrites['controller_server.ros__parameters.FollowPath.stateful']='false'
   node_params=ParameterFile(RewrittenYaml(source_file=params,param_rewrites=rewrites,
    convert_types=True),allow_substs=True)
  parameter_files=[node_params]
  if (name=='controller_server' and os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1'
      and os.environ.get('CH13_VALIDATION_SCENARIO') in ('level2_obstacles','level3_house')):
   parameter_files.append(str(share/'config/survey_navigation.yaml'))
  if (name in ('planner_server','controller_server','velocity_smoother') and os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1'
      and os.environ.get('CH13_EXPERIMENTAL_SE2')=='1'
      and os.environ.get('CH13_VALIDATION_SCENARIO') in ('level2_obstacles','level3_house')):
   parameter_files.append(str(share/'config/heading_aware_navigation.yaml'))
  if (name=='velocity_smoother' and os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1'
      and os.environ.get('CH13_VALIDATION_SCENARIO')=='level2_obstacles'):
   limits='level2_reverse_velocity_limits.yaml' if os.environ.get('CH13_EXPERIMENTAL_SE2')=='1' else 'level2_velocity_limits.yaml'
   parameter_files.append(str(share/'config'/limits))
  actions.append(Node(package=package,executable=executable,name=name,parameters=[*parameter_files,extra],remappings=remaps,output='screen'))
 actions.append(Node(package='nav2_lifecycle_manager',executable='lifecycle_manager',name='reuse_lifecycle_manager',parameters=[{'use_sim_time':True,'autostart':True,'bond_timeout':10.,'node_names':['planner_server','controller_server','velocity_smoother','bt_navigator']}],output='screen'))
 return LaunchDescription(actions)
