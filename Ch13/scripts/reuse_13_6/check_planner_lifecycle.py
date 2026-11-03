"""Owned planner-only lifecycle check; no physics, joint publisher or motion."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
import yaml
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from ament_index_python.packages import get_package_prefix
from ch13_piper_moveit_config.configuration import parameters


def scene_probe(node,report):
    import numpy as np
    root=Path(__file__).resolve().parents[3]
    sys.path.insert(0,str(root/'Ch13/ros2_ws/src/ch13_manipulation_reuse'))
    from ch13_manipulation_reuse.planning import Planner,object_cylinder
    from moveit_msgs.msg import PlanningSceneComponents
    from moveit_msgs.srv import ApplyPlanningScene,GetPlanningScene
    clients={name:node.create_client(typ,name) for typ,name in ((ApplyPlanningScene,'/apply_planning_scene'),(GetPlanningScene,'/get_planning_scene'))}
    def call(name,request,timeout=5.):
        client=clients[name];deadline=time.monotonic()+timeout
        while not client.service_is_ready() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.02)
        assert client.service_is_ready()
        future=client.call_async(request)
        while not future.done() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.01)
        assert future.done();return future.result()
    planner=Planner.__new__(Planner);planner.tcp=lambda:np.eye(4);planner.call=call;planner.revision=0;planner.records=[]
    planner.apply_objects([object_cylinder('scene_api_fixture',[.5,0.,.5])])
    def ids():
        request=GetPlanningScene.Request();request.components.components=(PlanningSceneComponents.WORLD_OBJECT_NAMES|PlanningSceneComponents.ROBOT_STATE_ATTACHED_OBJECTS)
        scene=call('/get_planning_scene',request).scene
        return dict(world=[obj.id for obj in scene.world.collision_objects],attached=[obj.object.id for obj in scene.robot_state.attached_collision_objects],
                    relative_z=[obj.object.pose.position.z+obj.object.primitive_poses[0].position.z for obj in scene.robot_state.attached_collision_objects])
    try:
        planner.attach_observed_cylinder('scene_api_fixture',[.5,0.,.5])
        first=ids();assert 'scene_api_fixture' not in first['world'] and 'scene_api_fixture' in first['attached']
        assert abs(first['relative_z'][0]-.5)<1e-6
        planner.attach_observed_cylinder('scene_api_fixture',[.5,0.,.51])
        second=ids();assert second['attached'].count('scene_api_fixture')==1
        assert abs(second['relative_z'][0]-.51)<1e-6
        report['scene_probe']=dict(scope='planning scene API only, NO physical grasp',first=first,updated=second,result='PASS')
    finally:
        report['scene_after_probe']=ids()
        for client in clients.values():node.destroy_client(client)


def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
    parameter_file=out/'planner.yaml'
    parameter_file.write_text(yaml.safe_dump({'reuse_move_group':{'ros__parameters':parameters()}}))
    executable=Path(get_package_prefix('ch13_manipulation_planner'))/'lib/ch13_manipulation_planner/planner_runtime'
    environment=dict(os.environ,ROS_DOMAIN_ID='136')
    report={'result':'FAIL','scope':'planner only, no engine/no motion'};log=(out/'planner.log').open('w')
    command=[str(executable),'--ros-args','--params-file',str(parameter_file)]
    if '--gdb' in sys.argv[2:]:command=['gdb','--batch','-ex','run','-ex','thread apply all bt','--args']+command
    process=subprocess.Popen(command,env=environment,stdout=log,stderr=subprocess.STDOUT)
    node=None
    try:
        rclpy.init(args=[],domain_id=136);node=Node('planner_lifecycle_check')
        client=node.create_client(Trigger,'/ch13/reuse/manipulation/planner/shutdown')
        deadline=time.monotonic()+15.
        while not client.service_is_ready():
            rclpy.spin_once(node,timeout_sec=.05)
            assert process.poll() is None,'planner exited at startup'
            assert time.monotonic()<deadline,'planner startup deadline'
        if '--scene-probe' in sys.argv[2:]:scene_probe(node,report)
        future=client.call_async(Trigger.Request());start=time.monotonic()
        while not future.done() and time.monotonic()-start<3.:rclpy.spin_once(node,timeout_sec=.02)
        assert future.done() and future.result().success,'shutdown ACK absent'
        process.wait(timeout=5.)
        report.update(exit_code=process.returncode,stop_wall_s=time.monotonic()-start)
        log.flush();assert process.returncode==0 and 'PLANNER_JOINED' in (out/'planner.log').read_text()
        report['result']='PASS'
    except BaseException:
        import traceback
        report['error']=traceback.format_exc()
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:process.wait(timeout=3.)
            except subprocess.TimeoutExpired:process.kill();process.wait();report['forced_cleanup']=True
        if node is not None:node.destroy_node();rclpy.try_shutdown()
        log.close();report['pid']=process.pid
        (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    return 0 if report['result']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
