"""Start observers before input, compare integrated/split with identical values."""
import hashlib,json,os,select,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path


def main():
    os.environ['ROS_DOMAIN_ID']='228';repo=Path.cwd();sys.path.insert(0,str(repo/'Ch13/scripts'))
    import rclpy
    from probe_navigation_13_5 import NavigationProbe,ProbeReceiver
    from split_observer_13_5 import SplitNavigationProbe
    from integrated_robot_navigation.g2_command_source import G2CommandSource
    from integrated_robot_navigation.carry_profile import default_limits
    helpers=Path(__file__).parent
    native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/('probe-split-cost-'+str(uuid.uuid4()));native.mkdir()
    fixture_source=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b/probe-process-cost-72d2eccf-5e9a-49f9-8bf4-e55bc43b78d1/payload_fixture.json'
    fixture=native/'payload_fixture.json';shutil.copyfile(fixture_source,fixture)
    for path in (Path(__file__),helpers/'replay-probe-payload.py',repo/'Ch13/scripts/split_observer_13_5.py',repo/'Ch13/scripts/probe_navigation_13_5.py'):shutil.copyfile(path,native/path.name)
    reports=[];failure=None;limits=default_limits();hz=os.sysconf('SC_CLK_TCK')
    def ticks(pid):
        v=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split();return int(v[11])+int(v[12])
    def delays(path):
        values=[];counts={}
        with path.open() as file:
            for line in file:
                row=json.loads(line);counts[row['kind']]=counts.get(row['kind'],0)+1
                if row['kind']=='body_transport':
                    v=row['value'];values.append((v['callback_system_ns']-v['rmw_received_system_ns'])/1e6)
        assert len(values)>=200
        values.sort();return dict(p95=values[int(.95*(len(values)-1))],maximum=max(values),count=len(values)),counts
    rclpy.init()
    try:
        for index,mode in enumerate(('integrated','split','split','integrated')):
            output=native/(str(index)+'-'+mode);output.mkdir();probe=receiver=command=command_receiver=peer=None;report=dict(mode=mode,index=index)
            try:
                probe=SplitNavigationProbe(output,engine='mujoco') if mode=='split' else NavigationProbe(output,engine='mujoco',bounded_history=True)
                receiver=ProbeReceiver(probe);probe.set_stage('stand')
                command=G2CommandSource(limits,trace_path=output/'commands.jsonl');command_receiver=ProbeReceiver(command);command.set_target(.01,0.)
                peer=subprocess.Popen([sys.executable,str(helpers/'replay-probe-payload.py'),'publisher',str(fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
                if not select.select([peer.stdout],[],[],10.)[0] or peer.stdout.readline().strip()!='READY':raise RuntimeError('synthetic source not ready')
                time.sleep(1.);before=probe.timing_snapshot();pid=probe.observer.identity['pid'] if mode=='split' else None;start_ticks=ticks(pid) if pid else 0
                start=time.monotonic();cpu=time.process_time();polls=0
                while time.monotonic()-start<5.:
                    probe.movement_decision(limits);polls+=1;time.sleep(.005)
                elapsed=time.monotonic()-start;used=time.process_time()-cpu
                report.update(polls=polls,wall_s=elapsed,parent_cpu_s=used,parent_one_core_percent=100*used/elapsed,full_observer_cpu_s=(ticks(pid)-start_ticks)/hz if pid else None,timing_before=before,timing_after=probe.timing_snapshot())
                receiver.check();command_receiver.check();assert not probe.errors and not probe.transport_errors
            finally:
                if peer is not None:
                    peer.send_signal(signal.SIGINT);stdout,stderr=peer.communicate(timeout=10.);(output/'publisher.stderr').write_text(stderr);report['publisher_exit']=peer.returncode
                    if peer.returncode:raise RuntimeError('owned synthetic source did not exit normally')
                if command is not None:
                    command.stop('diagnostic_end');assert command_receiver.shutdown(timeout_sec=5.);command.destroy_node()
                if receiver is not None:assert receiver.shutdown(timeout_sec=5.);report['receivers']=receiver.report()
                if probe is not None:
                    probe.restore_history(receiver_joined=True);report['journal']=probe.journal.report()
                    report['observer_process']=probe.observer.report() if mode=='split' else None
                    probe.close_log();probe.destroy_node()
            report['full_body_delay_ms'],report['full_counts']=delays(output/'observations.jsonl')
            assert report['full_counts'].get('frame',0)>=200
            if mode=='split':report['mission_body_delay_ms'],report['mission_counts']=delays(output/'mission_probe/observations.jsonl')
            reports.append(report)
    except BaseException as error:failure=repr(error)
    finally:
        rclpy.try_shutdown();out=dict(scope='same_original_values_new_synthetic_headers_NOT_engine_admission',order='observer_ready_before_input',failure=failure,reports=reports)
        with (native/'result.json').open('x') as file:json.dump(out,file,indent=2,allow_nan=False)
        dest=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'/native.name;shutil.copytree(native,dest);hashes={}
        for path in native.rglob('*'):
            if path.is_file():
                digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==hashlib.sha256((dest/path.relative_to(native)).read_bytes()).hexdigest();hashes[str(path.relative_to(native))]=digest
        with (dest/'COPY_SHA256.json').open('x') as file:json.dump(hashes,file,indent=2)
        print(json.dumps(dict(output=str(dest),failure=failure,reports=[{k:v for k,v in r.items() if k not in ('timing_before','timing_after','receivers','journal','observer_process','full_counts','mission_counts')} for r in reports]),indent=2))
    if failure:raise SystemExit(1)

if __name__=='__main__':main()
