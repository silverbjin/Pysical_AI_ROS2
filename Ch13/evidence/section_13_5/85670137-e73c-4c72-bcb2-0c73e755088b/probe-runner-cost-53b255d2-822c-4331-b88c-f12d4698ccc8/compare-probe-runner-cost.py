"""Unprofiled A/B with the same owned DDS publisher; no engine/admission proof."""
import hashlib,importlib.util,json,os,resource,select,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='228'
repo=Path.cwd();sys.path.insert(0,str(repo/'Ch13/scripts'))
import rclpy
key=str(uuid.uuid4());native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/('probe-runner-cost-'+key)
native.mkdir();helpers=Path(__file__).parent
paths={'baseline':helpers/'probe_before_immutable_records.py','immutable':repo/'Ch13/scripts/probe_navigation_13_5.py'}
modules={};sources={};reports=[];failure=None;peer=None
for name,path in paths.items():
    spec=importlib.util.spec_from_file_location('probe_compare_'+name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);modules[name]=module
    sources[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    shutil.copyfile(path,native/(name+'.py'))
for path in (__file__,str(helpers/'profile-probe-load.py'),str(repo/'Ch13/scripts/observation_records_13_5.py')):shutil.copyfile(path,native/Path(path).name)
try:
    peer=subprocess.Popen([sys.executable,str(helpers/'profile-probe-load.py'),'publisher'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    if not select.select([peer.stdout],[],[],10.)[0] or peer.stdout.readline().strip()!='READY':raise RuntimeError('peer not ready')
    rclpy.init()
    for index,variant in enumerate(('probe_only','with_command_source','with_command_and_poll')):
        name='baseline'
        module=modules[name];output=native/(str(index)+'-'+variant);output.mkdir();costs={};original=module.ProbeReceiver._spin
        def measured(self):
            label=self.node.get_name();start=time.monotonic();before=resource.getrusage(resource.RUSAGE_THREAD)
            try:original(self)
            finally:
                after=resource.getrusage(resource.RUSAGE_THREAD)
                costs[label]=dict(wall_s=time.monotonic()-start,cpu_s=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        module.ProbeReceiver._spin=measured
        probe=module.NavigationProbe(output,engine='mujoco',bounded_history=True);receiver=module.ProbeReceiver(probe)
        report=dict(variant=variant,index=index);source=source_receiver=None
        from integrated_robot_navigation.g2_command_source import G2CommandSource
        from integrated_robot_navigation.carry_profile import default_limits
        if variant!='probe_only':
            source=G2CommandSource(default_limits(),trace_path=output/'commands.jsonl');source_receiver=module.ProbeReceiver(source);source.set_target(.01,0.)
        try:
            time.sleep(1.);before=probe.timing_snapshot();start=time.monotonic();cpu=time.process_time();polls=0
            while time.monotonic()-start<5.:
                if variant=='with_command_and_poll':probe.movement_decision(default_limits());polls+=1
                time.sleep(.005)
            report['polls']=polls
            elapsed=time.monotonic()-start;used=time.process_time()-cpu;receiver.check()
            report.update(wall_s=elapsed,process_cpu_s=used,one_core_percent=100*used/elapsed,timing_before=before,timing_after=probe.timing_snapshot(),errors=list(probe.errors),transport_errors=list(probe.transport_errors))
        finally:
            if source is not None:
                source.stop('diagnostic_end');assert source_receiver.shutdown(timeout_sec=5.);report['command_receiver']=source_receiver.report();source.destroy_node()
            report['shutdown_ok']=receiver.shutdown(timeout_sec=5.);report['receivers']=receiver.report();report['thread_costs']=costs
            probe.close_log();probe.destroy_node();module.ProbeReceiver._spin=original
        reports.append(report)
        if not report['shutdown_ok'] or report['errors'] or report['transport_errors']:raise RuntimeError('observer diagnostic failed')
except BaseException as error:failure=repr(error)
finally:
    if rclpy.ok():rclpy.try_shutdown()
    if peer is not None:
        peer.send_signal(signal.SIGINT)
        try:stdout,stderr=peer.communicate(timeout=10.)
        except subprocess.TimeoutExpired:raise RuntimeError('owned publisher did not exit normally; do not launch an engine')
        (native/'publisher.stderr').write_text(stderr)
    out=dict(scope='unprofiled_synthetic_DDS_command_and_poll_cost_not_engine_acceptance',domain=228,sources=sources,reports=reports,failure=failure,publisher_reaped=peer is not None and peer.returncode is not None,publisher_exit=peer.returncode if peer else None)
    with (native/'result.json').open('x') as file:json.dump(out,file,indent=2,allow_nan=False)
    destination=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'/native.name;shutil.copytree(native,destination)
    hashes={}
    for source in native.rglob('*'):
        if source.is_file():
            sha=hashlib.sha256(source.read_bytes()).hexdigest();assert sha==hashlib.sha256((destination/source.relative_to(native)).read_bytes()).hexdigest();hashes[str(source.relative_to(native))]=sha
    with (destination/'COPY_SHA256.json').open('x') as file:json.dump(hashes,file,indent=2)
    print(json.dumps(dict(output=str(destination),failure=failure,reports=[{k:v for k,v in row.items() if k not in ('timing_before','timing_after','receivers','command_receiver')} for row in reports],publisher_exit=out['publisher_exit']),indent=2))
if failure or out['publisher_exit']!=0:raise SystemExit(1)
