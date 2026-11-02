"""Actual inactive controller dispatch, synthetic2ms work, no engine/motors."""
import hashlib,json,os,threading,time,uuid
from pathlib import Path
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock
from integrated_robot_navigation.crawl_controller import CrawlController
from integrated_robot_navigation.clock_execution import make_control_executor

base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
original=CrawlController._tick
out=dict(scope='inactive_controller_synthetic2ms_callback_no_engine_or_motor_acceptance',trials=[])
for direct in (False,True,True,False):
    ctx=Context();rclpy.init(context=ctx);rows=[]
    def work(node):
        start=time.monotonic_ns();cpu=time.thread_time_ns()
        while time.thread_time_ns()-cpu<2_000_000:pass
        rows.append(dict(wall_ns=start,elapsed_ns=time.monotonic_ns()-start,native_tid=threading.get_native_id()))
    CrawlController._tick=work
    node=CrawlController(engine='gazebo',context=ctx,
        cli_args=['--ros-args','-r','/clock:=/navigation/control_clock'],parameter_overrides=[
            Parameter('use_sim_time',value=True),Parameter('validation_mode',value=True),
            Parameter('control_clock_mode',value='relay100')])
    # A test-only startup selection before any model executor starts. Ingress
    # remains the same original wait-set for BOTH alternatives in this test.
    node.direct_model_dispatch=direct
    executor=make_control_executor(node);executor.add_node(node)
    peer=Node('bounded_model_clock_source',context=ctx)
    pub=peer.create_publisher(Clock,'/navigation/control_clock',10)
    stopping=threading.Event()
    def publish():
        index=0
        while not stopping.is_set():
            index+=10;msg=Clock();msg.clock.sec=index//1000;msg.clock.nanosec=index%1000*1000000
            pub.publish(msg);stopping.wait(.01)
    source=threading.Thread(target=publish,daemon=False);source.start()
    try:
        deadline=time.monotonic()+1.
        while time.monotonic()<deadline:executor.spin_once(timeout_sec=.005)
        rows.clear();wall=time.monotonic_ns();cpu=time.process_time_ns();deadline=wall+4_000_000_000
        while time.monotonic_ns()<deadline:executor.spin_once(timeout_sec=.005)
        elapsed=time.monotonic_ns()-wall;used=time.process_time_ns()-cpu
        frozen=list(rows);intervals=[(b['wall_ns']-a['wall_ns'])/1e6 for a,b in zip(frozen,frozen[1:])]
        out['trials'].append(dict(direct=direct,executor=type(executor).__name__,wall_ns=elapsed,
            process_cpu_ns=used,cpu_cores=used/elapsed,callbacks=len(frozen),
            min_interval_ms=min(intervals),max_interval_ms=max(intervals),
            callback_tids=sorted({r['native_tid'] for r in frozen}),
            command_publication_count=node.command_publication_count,active=node.active))
    finally:
        stopping.set();source.join(timeout=2.)
        if source.is_alive():raise RuntimeError('synthetic publisher did not join')
        if not executor.shutdown(timeout_sec=2.):raise RuntimeError('model executor did not join')
        node.destroy_node();peer.destroy_node();ctx.try_shutdown();CrawlController._tick=original
    out['trials'][-1].update(ingress_joined=node.ingress_worker.joined,ingress_error=node.ingress_worker.error)
target=base/('model-dispatch-'+str(uuid.uuid4())+'.json')
with target.open('x') as stream:json.dump(out,stream,indent=2)
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(target),trials=out['trials']),indent=2))
