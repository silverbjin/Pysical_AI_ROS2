"""Actual ROS callback-cost discriminator with explicit synthetic input only.

No engine. Fixture ACKs are not physics observations or acceptance evidence.
Run sequentially; profiler overhead prevents claiming native timing bounds.
"""
import cProfile,hashlib,json,os,pstats,statistics,sys,time,uuid
from pathlib import Path
repo=Path.cwd();task=repo/'.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO'
sys.path[:0]=[str(repo/'Ch13/ros2_ws/src/integrated_robot_navigation/test'),str(repo/'Ch13/scripts')]
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from sensor_msgs.msg import JointState
from rosgraph_msgs.msg import Clock
from builtin_interfaces.msg import Time
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation import clock_execution
from test_g2_control_cadence_ros import controller
from test_crawl_lifecycle import CrawlRig
from test_crawl_safety_ros import activate
from test_mujoco_relay_validation_scope import relay_proof
from test_execution_admission_contract import contract

closed=Path(sys.argv[1]);mode=sys.argv[2]
assert mode in ('pool','serial') and os.getuid()==1000
proof=json.loads((closed/'teardown.json').read_text())
assert proof['parent_reaped'] and not proof['residual_live_pids']
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
out=base/('diagnostic-owner-cost-'+mode+'-'+str(uuid.uuid4()));out.mkdir()
(out/'diagnostic-source.py').write_bytes(Path(__file__).read_bytes())
fixture_path=out/'SYNTHETIC_UNIT_FIXTURE_NOT_NATIVE_PROOF';fixture_path.mkdir()
result=json.loads((closed/'result.json').read_text())
model=compile_model(Path(result['scene']['robot']['path']).read_text())
profile,_,_=relay_proof(fixture_path,model,'a'*64)
if mode=='serial':clock_execution.make_control_executor=lambda node:SingleThreadedExecutor(context=node.context)
ctx=Context();rclpy.init(context=ctx);node=controller(ctx,model,profile,contract('mujoco'))
rig=CrawlRig(node,model,ctx);rig.node.destroy_publisher(rig.clock)
rig.clock=rig.node.create_publisher(Clock,'/navigation/control_clock',10)
echo=rig.node.create_publisher(JointState,'/navigation/applied_reference',1)
def ack(msg):
    value=JointState(name=list(model.joint_names),position=list(msg.data))
    sec=int(rig.capture);value.header.stamp=Time(sec=sec,nanosec=int((rig.capture-sec)*1e9))
    value.header.frame_id='mujoco/pre_step';echo.publish(value)
receiver=rig.node.create_subscription(type(__import__('std_msgs.msg',fromlist=['Float64MultiArray']).Float64MultiArray()),
    '/leg_position_controller/commands',ack,10)
profiler=cProfile.Profile();spans=[];original=node._tick
def tick():
    if not node.active or node.machine is None or node.machine.state!='CRAWL':return original()
    started=time.perf_counter_ns();profiler.enable()
    try:return original()
    finally:profiler.disable();spans.append(time.perf_counter_ns()-started)
node._tick=tick
value=dict(scope='synthetic_DDS_callback_profile_not_native_or_performance_acceptance',mode=mode,
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),uid=os.getuid(),
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    model_sha256=model.model_sha256,engine_attempts=0,errors=[])
try:
    rig.pump(.3);activate(rig);rig.ready=True
    rig.mode_name='CRAWL';rig.value=.001
    rig.pump(3.)
    value.update(state=node.machine.state,reason=node.machine.reason,stop_reason=node.stop_reason,
        publications=node.command_publication_count,profiled_ticks=len(spans),
        median_ns=statistics.median(spans) if spans else None,max_ns=max(spans) if spans else None)
except BaseException as error:
    value['errors'].append(repr(error));raise
finally:
    profiler.dump_stats(out/'callbacks.prof')
    with (out/'functions.txt').open('w') as stream:
        pstats.Stats(profiler,stream=stream).sort_stats('cumulative').print_stats(35)
    rig.node.destroy_subscription(receiver);rig.node.destroy_publisher(echo)
    rig.close();ctx.try_shutdown()
    value['ingress']=node.ingress_worker.snapshot();value['closed']=not ctx.ok()
    (out/'result.json').write_text(json.dumps(value,indent=2))
    print(json.dumps(dict(path=str(out),**value)),flush=True)
    print((out/'functions.txt').read_text(),flush=True)
