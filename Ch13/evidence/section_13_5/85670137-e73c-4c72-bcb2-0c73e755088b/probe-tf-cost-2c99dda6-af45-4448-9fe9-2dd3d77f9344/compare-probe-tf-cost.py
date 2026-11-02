"""Same synthetic DDS workload, old/new TF conversion; not engine acceptance."""
import hashlib,json,os,resource,select,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='228'
repo=Path.cwd();sys.path.insert(0,str(repo/'Ch13/scripts'))
import rclpy
from probe_navigation_13_5 import NavigationProbe,ProbeReceiver,RecordingNode
key=str(uuid.uuid4());native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/('probe-tf-cost-'+key)
native.mkdir();shutil.copyfile(__file__,native/Path(__file__).name)
peer=subprocess.Popen([sys.executable,str(Path(__file__).with_name('profile-probe-load.py')),'publisher'],
    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
factory=RecordingNode.create_subscription;spin=ProbeReceiver._spin;mode=None;thread_costs={};reports=[]
def subscribe(self,*args,**kwargs):
    if mode=='old_expanded':kwargs['raw']=False
    return factory(self,*args,**kwargs)
def measured(self):
    start=time.monotonic();before=resource.getrusage(resource.RUSAGE_THREAD)
    try:spin(self)
    finally:
        after=resource.getrusage(resource.RUSAGE_THREAD)
        thread_costs[self.node.get_name()]=dict(wall_s=time.monotonic()-start,
            cpu_s=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
try:
    if not select.select([peer.stdout],[],[],10.)[0] or peer.stdout.readline().strip()!='READY':raise RuntimeError('peer not ready')
    rclpy.init();RecordingNode.create_subscription=subscribe;ProbeReceiver._spin=measured
    for mode in ('old_expanded','new_raw'):
        output=native/mode;output.mkdir();probe=NavigationProbe(output,engine='mujoco',bounded_history=True)
        receiver=ProbeReceiver(probe)
        try:
            time.sleep(1.);start=time.monotonic();cpu=time.process_time();time.sleep(5.)
            elapsed=time.monotonic()-start;used=time.process_time()-cpu;receiver.check()
            report=dict(variant=mode,wall_s=elapsed,process_cpu_s=used,one_core_percent=100*used/elapsed,
                callback_costs=probe.timing_snapshot(),tf_api=probe.tf_api)
        finally:
            assert receiver.shutdown(timeout_sec=5.)
            report['thread_costs']=dict(thread_costs);report['receivers']=receiver.report()
            probe.close_log();probe.destroy_node()
        reports.append(report)
    rclpy.try_shutdown()
finally:
    RecordingNode.create_subscription=factory;ProbeReceiver._spin=spin
    peer.send_signal(signal.SIGINT);stdout,stderr=peer.communicate(timeout=10.)
    assert peer.returncode==0,(stdout,stderr)
out=dict(scope='synthetic_TF_conversion_cost_not_engine_physics_or_acceptance',domain=228,
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reports=reports,publisher_reaped=True,publisher_exit=peer.returncode)
with (native/'result.json').open('x') as file:json.dump(out,file,indent=2)
destination=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'/native.name
shutil.copytree(native,destination)
for source in native.rglob('*'):
    if source.is_file():assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256((destination/source.relative_to(native)).read_bytes()).digest()
print(json.dumps(dict(output=str(destination),reports=[{k:v for k,v in r.items() if k not in ('callback_costs','receivers')} for r in reports]),indent=2))
