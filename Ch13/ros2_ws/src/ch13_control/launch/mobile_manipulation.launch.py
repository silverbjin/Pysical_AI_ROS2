from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro
from ch13_control.launch_contract import validate_options

def setup(context):
    def arg(n):return LaunchConfiguration(n).perform(context)
    options=validate_options(arg('backend'),arg('enabled').lower()=='true',arg('headless').lower()=='true',arg('world'),arg('seed'))
    share=Path(get_package_share_directory('ch13_robot_description'))
    description=xacro.process_file(str(share/'urdf/integrated_robot.urdf.xacro')).toxml()
    common={'use_sim_time':True}
    actions=[Node(package='robot_state_publisher',executable='robot_state_publisher',parameters=[common,{'robot_description':description}]),
        Node(package='ch13_control',executable='state_monitor',parameters=[common]),
        Node(package='ch13_control',executable='command_arbiter_node',parameters=[common]),
        Node(package='ch13_control',executable='hold_controller',parameters=[common,{'enabled':options['enabled']}])]
    if options['backend']=='mujoco':
        actions.append(Node(package='ch13_control',executable='mujoco_bridge',parameters=[{'seed':options['seed']}]))
    else:
        from ch13_control.gazebo_router import gazebo_actions
        actions+=gazebo_actions(share,description,options)
    return actions
def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument(n,default_value=v) for n,v in [('backend','mujoco'),('enabled','false'),('headless','true'),('world',''),('seed','42')]]+[OpaqueFunction(function=setup)])
