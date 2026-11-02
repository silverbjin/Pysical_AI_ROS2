"""Actual child entrypoint: injected upstream loop retains existing cleanup."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_spin_accepts_context_bound_factory_without_changing_shutdown_protocol():
    source=str(Path(__file__).resolve().parents[1])
    program=r'''
import json,os,signal,sys
sys.path.insert(0,sys.argv[1])
import rclpy
from rclpy.node import Node
from rclpy.experimental.events_executor import EventsExecutor
from integrated_robot_runtime.common import spin
events=[]
class Owner(Node):
    def __init__(self):
        super().__init__('factory_cleanup_probe')
        self.count=0
        self.create_timer(.02,self.tick)
    def tick(self):
        self.count+=1
        if self.count==3:os.kill(os.getpid(),signal.SIGINT)
    def begin_shutdown(self):events.append('begin_shutdown')
    def shutdown_ready(self):return True
    def destroy_node(self):
        events.append('destroy_with_live_context' if self.context.ok() else 'context_destroyed_early')
        return super().destroy_node()
def factory(node):
    executor=EventsExecutor(context=node.context)
    assert executor.context is node.context
    events.append(type(executor).__name__)
    return executor
spin(Owner,threads=1,executor_factory=factory)
assert not rclpy.ok()
print(json.dumps(events))
'''
    result=subprocess.run([sys.executable,'-c',program,source],capture_output=True,text=True,timeout=12.,
        env=dict(os.environ,ROS_DOMAIN_ID='168'))
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout.splitlines()[-1])==['EventsExecutor','begin_shutdown','destroy_with_live_context']
    assert 'exception was never retrieved' not in result.stderr
