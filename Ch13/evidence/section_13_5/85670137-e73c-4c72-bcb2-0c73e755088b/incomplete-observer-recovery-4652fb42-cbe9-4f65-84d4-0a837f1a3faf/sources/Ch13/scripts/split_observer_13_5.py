"""Independent full ROS witness; only stage/finish RPC crosses its boundary."""
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
from pathlib import Path
import pickle
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


def _observe(directory,engine,connection):
    import rclpy
    from rclpy.signals import SignalHandlerOptions
    entry_wall_ns=time.monotonic_ns()
    os.setsid()  # Owned observer, independent of the console/engine groups.
    root=Path(directory);node=receiver=None;failure=None;runtime_fault=None;ipc=0;joined=False
    stat=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
    identity=dict(pid=os.getpid(),ppid=os.getppid(),uid=os.getuid(),pgid=os.getpgrp(),
        start_ticks=int(stat[19]),executable=sys.executable,module_files=_modules(),
        worker_entry_wall_ns=entry_wall_ns)
    try:
        rclpy.init(args=[],signal_handler_options=SignalHandlerOptions.NO)
        node=NavigationProbe(root,engine=engine,bounded_history=True)
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
        if node and joined:
            try:
                node.restore_history(receiver_joined=True)
                snapshot={name:getattr(node,name) for name in (
                    'frames','native_controls','body_references','transforms','errors',
                    'transport_errors','tf_api')}
                target=root/'observer_snapshot.pickle'
                with target.open('xb') as output:pickle.dump(snapshot,output,protocol=5)
                node.close_log()
                report=dict(identity=identity,receiver=receiver.report(),journal=node.journal.report(),
                    ipc_requests=ipc,failure=failure,runtime_fault=runtime_fault,snapshot=target.name,
                    snapshot_size=target.stat().st_size,snapshot_sha256=_digest(target))
                with (root/'observer_process_report.json').open('x') as output:json.dump(report,output,indent=2)
                node.destroy_node()
            except BaseException as error:failure=failure or repr(error)
        if rclpy.ok() and joined:rclpy.try_shutdown()
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
                or journal.get('joined') is not True or journal.get('error')
                or journal.get('submitted')!=journal.get('written')):
            self.error=self.error or 'observer finish failed: '+str(self.result.get('failure',self.process.exitcode))
            raise RuntimeError(self.error)
        try:
            path=(self.root/self.result['snapshot']).resolve(strict=True)
            if (not path.is_relative_to(self.root) or path.stat().st_uid!=os.getuid()
                    or path.stat().st_size!=self.result['snapshot_size']
                    or _digest(path)!=self.result['snapshot_sha256']):raise RuntimeError('observer snapshot ownership/hash')
            # Only the joined child created this private file; external/untrusted
            # files are never deserialized. Its original JSON remains authoritative.
            with path.open('rb') as source:self.data=pickle.load(source)
        except BaseException as error:
            self.error='observer snapshot: '+repr(error)
            raise RuntimeError(self.error) from error
        return self.data

    def report(self):
        return {**self.result,'joined':self.joined,'exitcode':self.process.exitcode,
            'ipc_requests':self.ipc_requests,'error':self.error,'runtime_fault':self.runtime_fault}


class SplitNavigationProbe(NavigationProbe):
    def __init__(self,directory,engine='mujoco',**kwargs):
        self.observer=ObserverProcess(directory,engine=engine)
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
        super().restore_history(receiver_joined=True)
        values=self.observer.finish(timeout_sec=20.)
        for name,value in values.items():
            if name in ('errors','transport_errors'):getattr(self,name).extend(value)
            else:setattr(self,name,value)
        self.full_restored=True
        if self.errors or self.transport_errors:
            raise RuntimeError('observer recorded input errors: '+str(self.errors+self.transport_errors))

    def destroy_node(self):
        if not self.observer.joined:raise RuntimeError('full observer still owns live resources')
        return super().destroy_node()
