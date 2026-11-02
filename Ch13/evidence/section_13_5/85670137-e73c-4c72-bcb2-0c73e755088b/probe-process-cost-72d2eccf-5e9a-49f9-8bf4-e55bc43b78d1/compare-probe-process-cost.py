"""Same real-valued synthetic DDS load, independent encoding ABBA; no engine."""
import hashlib,json,os,resource,select,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path

def main():
    os.environ['ROS_DOMAIN_ID']='228';repo=Path.cwd();sys.path.insert(0,str(repo/'Ch13/scripts'))
    import rclpy
    from probe_navigation_13_5 import NavigationProbe,ProbeReceiver
    from integrated_robot_navigation.g2_command_source import G2CommandSource
    from integrated_robot_navigation.carry_profile import default_limits
    helpers=Path(__file__).parent;key=str(uuid.uuid4());native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/('probe-process-cost-'+key);native.mkdir()
    source=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b/native-g1-mujoco-ba55d70f-e48b-423f-9f6b-639a5362e7ed'
    controls=frame=None
    with (source/'observations.jsonl').open() as file:
        for line in file:
            row=json.loads(line)
            if row['kind']=='native_controls':controls=row['value']
            if row['kind']=='frame' and row['value']['stage']=='stand' and controls is not None:frame=row['value'];break
    assert controls and frame
    fixture=native/'payload_fixture.json';fixture.write_text(json.dumps(dict(scope='original_values_new_synthetic_captures_not_physics',source_trial=source.name,source_copy_sha256=json.loads((source/'storage-copy-ledger.json').read_text())['files'],frame=frame,native_controls=controls)))
    for path in (Path(__file__),helpers/'replay-probe-payload.py',repo/'Ch13/scripts/process_journal_13_5.py',repo/'Ch13/scripts/probe_navigation_13_5.py'):shutil.copyfile(path,native/path.name)
    peer=None;failure=None;reports=[];limits=default_limits();hz=os.sysconf('SC_CLK_TCK')
    def child_ticks(pid):
        v=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split();return int(v[11])+int(v[12])
    try:
        peer=subprocess.Popen([sys.executable,str(helpers/'replay-probe-payload.py'),'publisher',str(fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        if not select.select([peer.stdout],[],[],10.)[0] or peer.stdout.readline().strip()!='READY':raise RuntimeError('source not ready')
        rclpy.init()
        for index,mode in enumerate(('thread','process','process','thread')):
            output=native/(str(index)+'-'+mode);output.mkdir();probe=NavigationProbe(output,engine='mujoco',bounded_history=True,journal_process=mode=='process');receiver=ProbeReceiver(probe)
            command=G2CommandSource(limits,trace_path=output/'commands.jsonl');command_receiver=ProbeReceiver(command);command.set_target(.01,0.);report=dict(mode=mode,index=index)
            try:
                time.sleep(1.);before=probe.timing_snapshot();pid=probe.journal.report().get('owner',{}).get('pid');ticks=child_ticks(pid) if pid else 0
                start=time.monotonic();cpu=time.process_time();polls=0
                while time.monotonic()-start<5.:
                    probe.movement_decision(limits);polls+=1;time.sleep(.005)
                elapsed=time.monotonic()-start;used=time.process_time()-cpu
                report.update(polls=polls,wall_s=elapsed,parent_cpu_s=used,parent_one_core_percent=100*used/elapsed,encoder_child_cpu_s=(child_ticks(pid)-ticks)/hz if pid else None,timing_before=before,timing_after=probe.timing_snapshot())
                receiver.check();command_receiver.check();assert not probe.errors and not probe.transport_errors
            finally:
                command.stop('diagnostic_end');assert command_receiver.shutdown(timeout_sec=5.);command.destroy_node()
                assert receiver.shutdown(timeout_sec=5.);report['receivers']=receiver.report()
                probe.restore_history(receiver_joined=True);report['journal']=probe.journal.report();probe.close_log();probe.destroy_node()
            delays=[];counts={}
            with (output/'observations.jsonl').open() as file:
                for line in file:
                    row=json.loads(line);counts[row['kind']]=counts.get(row['kind'],0)+1
                    if row['kind']=='body_transport':
                        v=row['value'];delays.append((v['callback_system_ns']-v['rmw_received_system_ns'])/1e6)
            assert len(delays)>=200 and counts.get('frame',0)>=200
            delays.sort();report['body_delay_ms']=dict(p95=delays[int(.95*(len(delays)-1))],maximum=max(delays),count=len(delays));report['counts']=counts;reports.append(report)
    except BaseException as error:failure=repr(error)
    finally:
        if rclpy.ok():rclpy.try_shutdown()
        if peer:
            peer.send_signal(signal.SIGINT);stdout,stderr=peer.communicate(timeout=10.);(native/'publisher.stderr').write_text(stderr)
            if peer.returncode:failure=failure or ('publisher exit '+str(peer.returncode))
        out=dict(scope='same_real_valued_DDS_replay_not_engine_acceptance',failure=failure,publisher_reaped=peer is not None and peer.returncode is not None,publisher_exit=peer.returncode if peer else None,reports=reports)
        with (native/'result.json').open('x') as file:json.dump(out,file,indent=2,allow_nan=False)
        dest=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'/native.name;shutil.copytree(native,dest);hashes={}
        for path in native.rglob('*'):
            if path.is_file():
                sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==hashlib.sha256((dest/path.relative_to(native)).read_bytes()).hexdigest();hashes[str(path.relative_to(native))]=sha
        with (dest/'COPY_SHA256.json').open('x') as file:json.dump(hashes,file,indent=2)
        print(json.dumps(dict(output=str(dest),failure=failure,publisher_exit=out['publisher_exit'],reports=[{k:v for k,v in r.items() if k not in ('receivers','timing_before','timing_after','counts','journal')} for r in reports]),indent=2))
    if failure:raise SystemExit(1)

if __name__=='__main__':main()
