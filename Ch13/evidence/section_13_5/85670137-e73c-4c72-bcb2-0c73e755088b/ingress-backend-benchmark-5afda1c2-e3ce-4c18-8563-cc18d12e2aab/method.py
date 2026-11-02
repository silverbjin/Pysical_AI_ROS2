"""Owned DDS receiver A/B, no engine/motor/model; not native acceptance."""
import hashlib,json,statistics,sys,time,uuid
from pathlib import Path
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.experimental.events_executor import EventsExecutor
from std_msgs.msg import UInt64
from integrated_robot_navigation.ingress_dispatch import IngressDispatch
from integrated_robot_navigation.dispatch_node import event_compatible_callback,event_backend_manifest

base=Path(sys.argv[1]);out=base/('ingress-backend-benchmark-'+str(uuid.uuid4()));out.mkdir()
trials=[]
for backend in ('waitset','events','events','waitset'):
    ctx=Context();rclpy.init(context=ctx);peer=Node('ingress_benchmark_source',context=ctx)
    received=[];transport=[];count=0
    def callback(msg,info):
        now=time.monotonic_ns();received.append((msg.data,now))
        field=lambda name:info[name] if isinstance(info,dict) else getattr(info,name)
        transport.append((field('source_timestamp'),field('received_timestamp')))
    subscriptions=[((UInt64,'/benchmark/ingress_'+str(i),event_compatible_callback(callback),5),{}) for i in range(8)]
    worker=IngressDispatch(ctx,'benchmark_ingress','/',subscriptions,autostart=False)
    if backend=='events':
        # Diagnostic prototype only, before the owned receiver thread starts.
        worker.executor.remove_node(worker.node);assert worker.executor.shutdown(timeout_sec=2.)
        worker.executor=EventsExecutor(context=ctx);worker.executor.add_node(worker.node)
    pubs=[peer.create_publisher(UInt64,'/benchmark/ingress_'+str(i),5) for i in range(8)]
    worker.start()
    try:
        deadline=time.monotonic()+3.
        while any(p.get_subscription_count()!=1 for p in pubs) and time.monotonic()<deadline:time.sleep(.01)
        assert all(p.get_subscription_count()==1 for p in pubs)
        clock=time.pthread_getcpuclockid(worker.thread.ident)
        cpu0=time.clock_gettime_ns(clock);begin=time.monotonic_ns();due=begin
        for index in range(300):
            pause=due-time.monotonic_ns()
            if pause>0:time.sleep(pause/1e9)
            for pub in pubs:pub.publish(UInt64(data=time.monotonic_ns()));count+=1
            due+=10_000_000
        time.sleep(.05);finish=time.monotonic_ns()
        assert worker.error is None,worker.error
        cpu=time.clock_gettime_ns(clock)-cpu0
        assert len(received)>=count*.95,(backend,len(received),count)
        delays=sorted(b-a for a,b in received)
        trials.append(dict(backend=backend,sent=count,received=len(received),wall_ns=finish-begin,
            receiver_thread_cpu_ns=cpu,cpu_fraction=cpu/(finish-begin),
            callback_delay_median_ns=statistics.median(delays),callback_delay_p95_ns=delays[int((len(delays)-1)*.95)],
            callback_delay_max_ns=max(delays),message_info_preserved=all(a>0 and b>0 for a,b in transport)))
        (out/'progress.json').write_text(json.dumps(trials,indent=2))
    except BaseException as error:
        (out/'failure.json').write_text(json.dumps(dict(error=repr(error),worker=worker.snapshot(),trials=trials),indent=2))
        raise
    finally:
        worker.close();peer.destroy_node();ctx.try_shutdown()
    assert worker.joined and not worker.thread.is_alive()
value=dict(scope=__doc__,method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    dependency=event_backend_manifest(),trials=trials,
    limitation='Eight UInt64 streams isolate dispatch overhead; actual typed sensor parsing/model/engine load are not simulated.')
(out/'method.py').write_bytes(Path(__file__).read_bytes())
(out/'result.json').write_text(json.dumps(value,indent=2))
print(json.dumps(dict(output=str(out),trials=trials)),flush=True)
