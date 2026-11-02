"""Independent full ROS witness; only stage/finish RPC crosses its boundary."""
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import time

from probe_navigation_13_5 import NavigationProbe,ProbeReceiver


def _digest(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as file:
        for block in iter(lambda:file.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def _modules():
    return {name:str(Path(importlib.util.find_spec(name).origin).resolve()) for name in
        ('integrated_robot_navigation','integrated_robot_runtime','integrated_robot_vision')}


_STREAMS=dict(frame='frames',native_controls='native_controls',
    body_reference='body_references',tf_transform='transforms')


def _seal_recording(node):
    """Receivers must already be joined. Close the writer, keep the live cache bounded."""
    node.close_log()
    journal=node.journal.report()
    if (journal.get('joined') is not True or journal.get('error')
            or journal['submitted']!=journal['written']):
        raise RuntimeError('observer journal close/count not confirmed')
    path=node.journal_path
    report=dict(scope='sealed_complete_journal_requires_post_join_validation',
        journal_path=path.name,journal_size=path.stat().st_size,journal_sha256=_digest(path),
        capture_records=getattr(node,'capture_records',False),
        counts=dict(node.journal_counts),records=journal['written'],live_cache_limit=128,
        live_lengths={name:len(getattr(node,name)) for name in _STREAMS.values()},
        gc_policy_changed=False,gc_spans=list(node.gc_spans),observer_timing=node.timing_snapshot(),
        errors=list(node.errors),transport_errors=list(node.transport_errors),tf_api=node.tf_api)
    with (path.parent/'recording_report.json').open('x') as output:
        json.dump(report,output,indent=2,allow_nan=False)
    return report


def _load_recording(root,report,*,retain=True):
    """After process join: validate EVERY original row/hash/count, never only the cache."""
    root=Path(root).resolve(strict=True)
    binary=report.get('capture_records',False)
    expected_path='observations.capture' if binary else 'observations.jsonl'
    if report['journal_path']!=expected_path:raise RuntimeError('observer journal ownership/path')
    path=(root/report['journal_path']).resolve(strict=True)
    if (path.parent!=root or path.stat().st_uid!=os.getuid()
            or path.stat().st_size!=report['journal_size']):
        raise RuntimeError('observer journal ownership/size')
    counts={key:0 for key in _STREAMS};values={name:[] for name in _STREAMS.values()}
    sha=hashlib.sha256();records=0;export=None;export_sha=hashlib.sha256()
    json_path=root/'observations.jsonl';temporary=root/'observations.jsonl.tmp'
    if binary:
        # Check identity/hash BEFORE any binary decoding. The restricted reader
        # additionally forbids classes and persistent references.
        if _digest(path)!=report['journal_sha256']:raise RuntimeError('observer capture hash')
        if not json_path.exists():export=temporary.open('x',encoding='utf-8')
    try:
        with path.open('rb') as source:
            if binary:
                from observer_journal_13_5 import read_records
                rows=read_records(source)
            else:
                def json_rows():
                    for line in source:
                        sha.update(line);yield json.loads(line)
                rows=json_rows()
            for row in rows:
                records+=1;kind=row['kind']
                if kind in _STREAMS:
                    counts[kind]+=1
                    if retain:values[_STREAMS[kind]].append(row['value'])
                if binary:
                    encoded=json.dumps(row,allow_nan=False)+'\n'
                    export_sha.update(encoded.encode('utf-8'))
                    if export:export.write(encoded)
    finally:
        if export:export.close()
    actual_sha=_digest(path) if binary else sha.hexdigest()
    if (actual_sha!=report['journal_sha256'] or records!=report['records']
            or any(counts[key]!=report['counts'].get(key,0) for key in _STREAMS)):
        raise RuntimeError('observer journal hash/record count differs from closed writer')
    if binary:
        if export:temporary.rename(json_path)
        if _digest(json_path)!=export_sha.hexdigest():raise RuntimeError('observer JSON export hash')
    if not retain:return None
    return dict(**values,**{name:report[name] for name in ('errors','transport_errors','tf_api')})


def _observe(directory,engine,connection):
    import rclpy
    from rclpy.signals import SignalHandlerOptions
    entry_wall_ns=time.monotonic_ns()
    os.setsid()  # Owned observer, independent of the console/engine groups.
    root=Path(directory);node=receiver=None;failure=None;runtime_fault=None;ipc=0;joined=False
    recording=None;ros_closed=False;receiver_report={}
    stat=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
    identity=dict(pid=os.getpid(),ppid=os.getppid(),uid=os.getuid(),pgid=os.getpgrp(),
        start_ticks=int(stat[19]),executable=sys.executable,module_files=_modules(),
        worker_entry_wall_ns=entry_wall_ns)
    try:
        rclpy.init(args=[],signal_handler_options=SignalHandlerOptions.NO)
        node=NavigationProbe(root,engine=engine,bounded_history=True,capture_records=True)
        identity['node_ready_wall_ns']=time.monotonic_ns()
        receiver=ProbeReceiver(node)
        identity['receiver_ready_wall_ns']=time.monotonic_ns()
        with (root/'observer_startup.json').open('x') as output:json.dump(identity,output,indent=2)
        connection.send(('ready',identity))
        notice_sent=False
        while True:
            receiver.check()
            fault=node.fault()
            if fault and not node.ignore_faults and not notice_sent:
                runtime_fault=dict(reason=fault,stage=node.stage,
                    ros_ns=node.get_clock().now().nanoseconds,wall_ns=time.monotonic_ns())
                connection.send(('fault',runtime_fault));notice_sent=True
            if not connection.poll(.01):continue
            command,value=connection.recv();ipc+=1
            if command=='stage':
                node.set_stage(value,ignore_faults=True if value=='shutdown' else None)
                connection.send(('stage',value))
            elif command=='transforms':connection.send(('transforms',node.transform_snapshot()))
            elif command=='stop':break
            else:raise ValueError('unknown observer command')
    except BaseException as error:
        failure=repr(error)
        try:connection.send(('error',failure))
        except (OSError,EOFError):pass
    finally:
        if receiver:
            joined=receiver.shutdown(timeout_sec=2.)
            if not joined:
                failure=failure or 'observer receiver shutdown exceeded original deadline'
                # A missed join is permanently failed. Retain live ROS resources
                # until the current callbacks finish; never kill or restart them.
                while not receiver.shutdown(timeout_sec=.1):pass
                joined=True
            receiver_report=receiver.report()
        if node and joined:
            try:
                recording=_seal_recording(node)
                node.destroy_node()
                ros_closed=True
            except BaseException as error:failure=failure or repr(error)
        if rclpy.ok() and joined:
            try:rclpy.try_shutdown()
            except BaseException as error:
                failure=failure or repr(error);ros_closed=False
        report=dict(identity=identity,receiver=receiver_report,
            journal=node.journal.report() if node and node.journal else {},recording=recording,
            ipc_requests=ipc,failure=failure,runtime_fault=runtime_fault,ros_closed=ros_closed)
        with (root/'observer_process_report.json').open('x') as output:
            json.dump(report,output,indent=2,allow_nan=False)
        connection.close()
    if failure:raise SystemExit(1)


class ObserverProcess:
    def __init__(self,directory,*,engine):
        self.root=Path(directory).resolve(strict=True);self.finished=False;self.data=None
        self.joined=False;self.ipc_requests=0;self.error=None;self.result={}
        self.runtime_fault=None
        ctx=mp.get_context('spawn');self.connection,child=ctx.Pipe()
        self.process=ctx.Process(target=_observe,args=(str(self.root),engine,child),name='navigation_full_observer')
        self.spawn_requested_wall_ns=time.monotonic_ns()
        self.process.start();child.close()
        self.spawn_returned_wall_ns=time.monotonic_ns()
        try:
            # Setup completes BEFORE any engine starts. This independent cold
            # import/readiness bound does not change the 10s physical G1 gate.
            kind,self.identity=self._receive(30.)
            self.identity.update(spawn_requested_wall_ns=self.spawn_requested_wall_ns,
                spawn_returned_wall_ns=self.spawn_returned_wall_ns,
                parent_ready_received_wall_ns=time.monotonic_ns())
            if kind!='ready':raise RuntimeError('observer startup: '+str(self.identity))
            if (self.identity['pid']!=self.process.pid or self.identity['uid']!=os.getuid()
                    or self.identity['module_files']!=_modules()):raise RuntimeError('observer identity/package mismatch')
        except BaseException:
            self.finish(timeout_sec=20.)
            raise

    def _receive(self,seconds):
        if not self.connection.poll(seconds):raise RuntimeError('observer response deadline')
        try:return self.connection.recv()
        except EOFError:raise RuntimeError('observer exited without response') from None

    def _notice(self,kind,value):
        if kind=='fault':self.runtime_fault=value
        else:
            self.error='observer '+kind+': '+str(value)
            raise RuntimeError(self.error)

    def check(self,*,allow_runtime_fault=False):
        if self.error:raise RuntimeError(self.error)
        while not self.finished and self.connection.poll():
            try:kind,value=self.connection.recv()
            except EOFError:kind,value='error','observer connection closed'
            self._notice(kind,value)
        if not self.finished and self.process.exitcode is not None:
            self.error='observer exited before finish: '+str(self.process.exitcode)
            raise RuntimeError(self.error)
        if self.runtime_fault and not allow_runtime_fault:
            raise RuntimeError('observer runtime fault: '+str(self.runtime_fault))

    def _request(self,kind,value=None,*,allow_runtime_fault=False):
        self.check(allow_runtime_fault=allow_runtime_fault)
        self.connection.send((kind,value));self.ipc_requests+=1;deadline=time.monotonic()+3.
        while True:
            reply,data=self._receive(max(0.,deadline-time.monotonic()))
            if reply==kind:break
            self._notice(reply,data)
        if self.runtime_fault and not allow_runtime_fault:
            raise RuntimeError('observer runtime fault: '+str(self.runtime_fault))
        return data

    def set_stage(self,stage):
        if stage not in ('bootstrap','stand','calibrate','forward','left','right','reverse','stopped','shutdown'):
            raise ValueError('unknown observer stage')
        if self._request('stage',stage,allow_runtime_fault=stage=='shutdown')!=stage:
            raise RuntimeError('observer stage acknowledgement mismatch')

    def transforms(self):return self._request('transforms')

    def finish(self,*,timeout_sec):
        if self.finished:
            if self.error:raise RuntimeError(self.error)
            return self.data
        if not getattr(self,'stop_sent',False):
            if self.process.is_alive():
                try:self.connection.send(('stop',None));self.ipc_requests+=1
                except (BrokenPipeError,EOFError,OSError):pass
            self.stop_sent=True
        self.process.join(timeout=timeout_sec)
        if self.process.is_alive():raise RuntimeError('observer process not joined; resources retained')
        self.joined=True
        report_path=self.root/'observer_process_report.json'
        if report_path.exists():self.result=json.loads(report_path.read_text())
        self.runtime_fault=self.runtime_fault or self.result.get('runtime_fault')
        self.finished=True;self.connection.close()
        journal=self.result.get('journal',{})
        if (self.error or self.process.exitcode!=0 or self.result.get('failure')
                or not self.result.get('receiver',{}).get('closed')
                or self.result.get('ros_closed') is not True
                or journal.get('joined') is not True or journal.get('error')
                or journal.get('submitted')!=journal.get('written')):
            self.error=self.error or 'observer finish failed: '+str(self.result.get('failure',self.process.exitcode))
            raise RuntimeError(self.error)
        try:
            self.data=_load_recording(self.root,self.result['recording'])
        except BaseException as error:
            self.error='observer journal: '+repr(error)
            raise RuntimeError(self.error) from error
        return self.data

    def report(self):
        return {**self.result,'joined':self.joined,'exitcode':self.process.exitcode,
            'ipc_requests':self.ipc_requests,'error':self.error,'runtime_fault':self.runtime_fault}


class SplitNavigationProbe(NavigationProbe):
    def __init__(self,directory,engine='mujoco',*,observer_backend='python',**kwargs):
        if observer_backend=='native_cdr':
            from native_observer_13_5 import NativeObserverProcess
            observer_type=NativeObserverProcess
        elif observer_backend=='python':observer_type=ObserverProcess
        else:raise ValueError('unknown observer backend')
        self.observer=observer_type(directory,engine=engine)
        mission=Path(directory)/'mission_probe';mission.mkdir()
        try:super().__init__(mission,engine=engine,bounded_history=True,mission_only=True,**kwargs)
        except BaseException:
            self.observer.finish(timeout_sec=20.)
            raise
        self.full_restored=False

    def set_stage(self,stage,*,ignore_faults=None):
        super().set_stage(stage,ignore_faults=ignore_faults)
        self.observer.set_stage(stage)  # ACK before caller can issue the next goal.

    def fault(self):
        self.observer.check()
        return super().fault()

    def transform_snapshot(self):return self.observer.transforms()

    def restore_history(self,*,receiver_joined):
        if not receiver_joined:raise RuntimeError('mission receiver must be joined')
        if self.full_restored:return
        # Do not materialize the redundant mission history or ask the child
        # to decode/pickle its whole journal inside the unchanged 20s join.
        mission_report=_seal_recording(self)
        values=self.observer.finish(timeout_sec=20.)
        _load_recording(self.journal_path.parent,mission_report,retain=False)
        for name,value in values.items():
            if name in ('selected_prefixes','missing','counts'):continue
            if name in ('errors','transport_errors'):getattr(self,name).extend(value)
            else:setattr(self,name,value)
        self.full_restored=True
        self.history_restored=True
        if self.errors or self.transport_errors:
            raise RuntimeError('observer recorded input errors: '+str(self.errors+self.transport_errors))

    def destroy_node(self):
        if not self.observer.joined:raise RuntimeError('full observer still owns live resources')
        return super().destroy_node()
