"""Original short DDS load + native/NumPy exact-state math; inactive owner, zero motors/engines."""
import hashlib,json,os,pickle,statistics,subprocess,sys,time,uuid
from pathlib import Path

def raw():return time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)

def fixture(path):
    metadata=json.loads((path/'manifest.json').read_text());payload=(path/'trusted-packets.pickle').read_bytes()
    assert hashlib.sha256(payload).hexdigest()==metadata['fixture_sha256']
    # Only this tool's local CRC/hash-validated subset is loaded, never user pickle.
    return metadata,pickle.loads(payload)

def source(path):
    import rclpy
    from rclpy.context import Context
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data,QoSProfile,ReliabilityPolicy
    from native_observer_13_5 import _message_types
    from rosgraph_msgs.msg import Clock
    metadata,packets=fixture(path);types=_message_types();types['clock']=Clock
    topics=dict(joints='/joint_states',imu='/navigation/imu',contacts='/navigation/foot_contacts',body='/odom',
        scan='/scan',carry='/navigation/carry_state',guard_state='/navigation/guard_state',
        applied_reference='/navigation/applied_reference',clock='/navigation/control_clock')
    ctx=Context();rclpy.init(context=ctx,domain_id=222);node=Node('contention_source',context=ctx)
    clock_qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT)
    pubs={k:node.create_publisher(types[k],topic,
        clock_qos if k=='clock' else 1 if k in ('guard_state','applied_reference') else qos_profile_sensor_data)
        for k,topic in topics.items()}
    try:
        deadline=raw()+5_000_000_000
        while any(p.get_subscription_count()!=1 for p in pubs.values()) and raw()<deadline:time.sleep(.005)
        assert all(p.get_subscription_count()==1 for p in pubs.values()),{k:p.get_subscription_count() for k,p in pubs.items()}
        begin=raw();max_late=0
        for offset,key,payload,_ in packets:
            due=begin+offset
            while True:
                pause=due-raw()
                if pause<=0:break
                time.sleep(min(pause/1e9,.001))
            max_late=max(max_late,raw()-due);pubs[key].publish(payload)
        return dict(begin_raw_ns=begin,end_raw_ns=raw(),packets=len(packets),max_lateness_ns=max_late)
    finally:node.destroy_node();ctx.try_shutdown()

def worker(path,mode):
    assert mode in ("numpy","native")
    import rclpy
    from rclpy.context import Context
    from rclpy.parameter import Parameter
    import numpy as np
    from integrated_robot_navigation.crawl_controller import CrawlController
    from integrated_robot_navigation.clock_execution import make_control_executor
    from integrated_robot_navigation.model import compile_model
    from integrated_robot_navigation.gait import CrawlMachine
    from integrated_robot_navigation.samples import Sample,SensorBundle
    metadata,_=fixture(path);root=Path(metadata['original_trial'])
    report=json.loads((root/'controller_report.json').read_text());result=json.loads((root/'result.json').read_text())
    robot=Path(result['scene']['robot']['path']);model=compile_model(robot.read_text())
    assert model.model_sha256==report['model_sha256']
    fault=report['first_fault'];bundle=SensorBundle(**{k:Sample(**v) if v else None for k,v in fault['samples'].items()})
    value=CrawlMachine(model,json.loads((root/'validated_profile.json').read_text())['limits']);value.state='CRAWL'
    value.reference_body=np.asarray(fault['reference_body']);value._targets={k:np.asarray(v) for k,v in fault['targets'].items()}
    q=fault['samples']['joints']['data']['position']
    def arithmetic():value._measure(bundle,fault['ros_ns'],fault['wall_ns']);return value._solve(q,True)
    expected=arithmetic();samples=[]
    core=None
    if mode=="native":
        from integrated_robot_navigation.native_mass import NativeMassEvaluator
        import integrated_robot_navigation.gait as gait_module
        core=NativeMassEvaluator(model)
        gait_module.center_of_mass=core
        assert arithmetic()==expected
    ctx=Context();rclpy.init(context=ctx,domain_id=222)
    profile=result['execution_mode']['native_execution_profile']
    node=CrawlController(model,None,'mujoco',context=ctx,
        cli_args=['--ros-args','-r','/clock:=/navigation/control_clock'],parameter_overrides=[
            Parameter('use_sim_time',value=True),Parameter('validation_mode',value=True),
            Parameter('g2_validation_mode',value=True),Parameter('control_clock_mode',value='relay100'),
            Parameter('native_execution_profile',value=json.dumps(profile))])
    def measured_math():
        a=raw();cpu=time.thread_time_ns();answer=arithmetic()
        assert answer==expected
        samples.append(dict(begin_raw_ns=a,end_raw_ns=raw(),cpu_ns=time.thread_time_ns()-cpu))
    # Diagnostic instrumentation only; no lifecycle activation, model advance,
    # command gate bypass, target publication, or acceptance verdict.
    node._tick=measured_math
    executor=make_control_executor(node);executor.add_node(node)
    command=[sys.executable,str(Path(__file__).resolve()),'--source',str(path)]
    stderr=path/('source-'+str(uuid.uuid4())+'.stderr')
    with stderr.open('xb') as errors:
        child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=errors)
        try:
            deadline=raw()+20_000_000_000
            while child.poll() is None and raw()<deadline:executor.spin_once(timeout_sec=.02)
            if child.poll() is None:raise RuntimeError('owned diagnostic source did not close; process retained')
            output=child.stdout.read().decode();assert child.returncode==0,(child.returncode,stderr.read_text())
            sent=json.loads(output)
            selected=[r for r in samples if sent['begin_raw_ns']<=r['begin_raw_ns']<=sent['end_raw_ns']]
            assert selected and node.command_publication_count==0 and not node.active and node.machine is None
            def stats(values):
                v=sorted(values);return dict(count=len(v),mean_ns=statistics.mean(v),median_ns=statistics.median(v),p95_ns=v[int((len(v)-1)*.95)],max_ns=max(v))
            result=dict(mode=mode,interval=sys.getswitchinterval(),source=sent,math_wall=stats([r['end_raw_ns']-r['begin_raw_ns'] for r in selected]),
                math_cpu=stats([r['cpu_ns'] for r in selected]),numeric_outputs_identical=True,
                timer_gaps=stats([b['begin_raw_ns']-a['begin_raw_ns'] for a,b in zip(selected,selected[1:])]),
                callbacks=len(selected),motor_publications=node.command_publication_count,ingress=node.ingress_worker.snapshot(),
                scope=__doc__,source_command=command,source_exit=child.returncode)
        finally:
            executor.shutdown(timeout_sec=2.);node.destroy_node();ctx.try_shutdown()
    assert node.ingress_worker.joined
    result['ingress_joined']=node.ingress_worker.joined
    if core is not None:
        result['native_mass']=core.provenance;core.close()
    return result

repo=Path.cwd();sys.path.insert(0,str(repo/'Ch13/scripts'))
if sys.argv[1]=='--source':print(json.dumps(source(Path(sys.argv[2]))));raise SystemExit(0)
if sys.argv[1]=='--worker':print(json.dumps(worker(Path(sys.argv[2]),sys.argv[3])));raise SystemExit(0)
path=Path(sys.argv[1]);base=Path(sys.argv[2]);out=base/('native-mass-contention-replay-'+str(uuid.uuid4()));out.mkdir();rows=[]
(out/'method.py').write_bytes(Path(__file__).read_bytes())
for index,mode in enumerate(("numpy","native","native","numpy")):
    command=[sys.executable,str(Path(__file__).resolve()),'--worker',str(path),mode]
    child=subprocess.run(command,capture_output=True,text=True)
    (out/f'child-{index}.stdout').write_text(child.stdout);(out/f'child-{index}.stderr').write_text(child.stderr)
    if child.returncode:
        (out/'failure.json').write_text(json.dumps(dict(command=command,exit=child.returncode,stderr=child.stderr)))
        raise SystemExit(child.stderr)
    rows.append(json.loads(child.stdout));(out/'progress.json').write_text(json.dumps(rows,indent=2))
(out/'result.json').write_text(json.dumps(dict(scope=__doc__,fixture=str(path),trials=rows),indent=2))
print(json.dumps(dict(output=str(out),trials=[{k:v for k,v in row.items() if k not in ('ingress','source_command')} for row in rows])))
