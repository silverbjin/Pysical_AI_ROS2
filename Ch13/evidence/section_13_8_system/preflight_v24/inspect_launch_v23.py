import importlib.util,os,json,tempfile
from pathlib import Path
import rclpy,yaml
from rclpy.context import Context
from ament_index_python.packages import get_package_share_directory
root=Path(__import__('sys').argv[1])
os.environ['CH13_VALIDATION_PROFILE']='carry_v1';os.environ['CH13_VALIDATION_SCENARIO']='level1_floor'
share=Path(get_package_share_directory('ch13_navigation_reuse'));print('SHARE',share)
spec=importlib.util.spec_from_file_location('nav_launch',share/'launch/navigation.launch.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for action in module.generate_launch_description().entities:
    if type(action).__name__=='Node':print('NODE_PARAMS',str(getattr(action,'_Node__node_name',None)),str(getattr(action,'_Node__parameters',None))[-350:])
with tempfile.TemporaryDirectory() as tmp:
    override=Path(tmp)/'override.yaml';override.write_text(yaml.safe_dump({'/**':{'ros__parameters':{'goal_checker.xy_goal_tolerance':.015}}}))
    context=Context();rclpy.init(context=context)
    node=rclpy.create_node('controller_server',context=context,use_global_arguments=False,
        cli_args=['--ros-args','--params-file',str(share/'config/nav2_params.yaml'),'--params-file',str(override)],
        automatically_declare_parameters_from_overrides=True)
    print('RCLPY_EFFECTIVE',node.get_parameter('goal_checker.xy_goal_tolerance').value)
    node.destroy_node();context.shutdown()