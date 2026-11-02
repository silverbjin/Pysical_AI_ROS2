"""Real inactive ROS owner + frozen arithmetic; no controller/engine/commands."""
import sys,json,time,hashlib,threading,os
from pathlib import Path
import numpy as np
root=Path.cwd();src=root/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(src))
import rclpy
from rclpy.context import Context
from rclpy.parameter import Parameter
from integrated_robot_navigation.crawl_controller import CrawlController
from integrated_robot_navigation.clock_execution import make_control_executor
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.scene import load_scene
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.samples import Sample,SensorBundle
trial='native-g1-gazebo-330b055b-0cb9-4db5-872d-06e2613fe447'
base=root/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
report_path=base/trial/'controller_report.json';report=json.loads(report_path.read_text());f=report['first_fault']
scene=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/(trial+'-prepared')/'scene'
model=compile_model(Path(load_scene('gazebo',scene)['robot']['path']).read_text())
bundle=SensorBundle(**{k:Sample(**v) if v else None for k,v in f['samples'].items()})
m=CrawlMachine(model,default_limits());m.reference_body=np.array(f['reference_body']);m._targets={n:np.array(v) for n,v in f['targets'].items()}
ctx=Context();rclpy.init(context=ctx)
node=CrawlController(engine='gazebo',context=ctx,parameter_overrides=[
    Parameter('validation_mode',value=True),Parameter('control_clock_mode',value='relay100')])
mode=sys.argv[1];assert mode in ('pool','direct')
node.direct_model_dispatch=mode=='direct'  # experiment only, before dispatch starts
executor=make_control_executor(node);executor.add_node(node);cost=[]
def compute():
    begin=time.perf_counter_ns();cpu=time.thread_time_ns()
    q,_,_,_,_,_=m._measure(bundle,f['ros_ns'],f['wall_ns']);m._solve(q,False)
    cost.append(dict(wall_ns=time.perf_counter_ns()-begin,cpu_ns=time.thread_time_ns()-cpu))
node.create_timer(.02,compute)
start=time.monotonic_ns();cpu=time.process_time_ns()
try:
    while time.monotonic_ns()-start<3_000_000_000:executor.spin_once(timeout_sec=.01)
    elapsed=time.monotonic_ns()-start;used=time.process_time_ns()-cpu
    assert not node.active and node.command_publication_count==0
finally:
    executor.shutdown(timeout_sec=2.);node.destroy_node();ctx.try_shutdown()
out=dict(scope='controlled_inactive_owner_frozen_arithmetic_not_engine',mode=mode,
    executor=type(executor).__name__,wall_ns=elapsed,cpu_ns=used,
    process_cpu_percent=used/elapsed*100.,calls=len(cost),samples=cost,
    report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    no_motor_publications=True,ingress_joined=node.ingress_worker.joined)
path=base/('task8-g1-executor-'+mode+'-01.json');assert not path.exists();path.write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k!='samples'}))
