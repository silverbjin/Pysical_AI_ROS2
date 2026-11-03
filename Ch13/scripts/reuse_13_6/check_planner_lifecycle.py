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
