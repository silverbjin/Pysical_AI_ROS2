"""Owned native CDR witness. Decode only after its ROS receiver has exited.

Wire receipt and frame cutoff are taken by the native receiver, never by this
offline interpreter. This file does not issue robot or clock commands.
"""
from collections import Counter,deque
from dataclasses import asdict
import json
from pathlib import Path
import struct
from threading import RLock
import zlib

MAGIC=b'CH13CDR1\n'
MAX_RECORD=8*1024*1024


def read_records(source):
    if source.read(len(MAGIC))!=MAGIC:raise ValueError('CDR journal magic')
    sequence=0
    while True:
        prefix=source.read(8)
        if len(prefix)!=8:raise ValueError('CDR journal missing closed footer or truncated prefix')
        size,checksum=struct.unpack('<II',prefix)
        if not 6<=size<=MAX_RECORD:raise ValueError('CDR record size')
        body=source.read(size)
        if len(body)!=size or zlib.crc32(body)!=checksum:raise ValueError('CDR record truncated/CRC')
        length=struct.unpack('<I',body[:4])[0]
        if not 2<=length<=min(65536,size-4):raise ValueError('CDR metadata size')
        meta=json.loads(body[4:4+length]);sequence+=1
        if not isinstance(meta,dict) or type(meta.get('sequence')) is not int or meta['sequence']!=sequence:
            raise ValueError('CDR record sequence')
        if meta.get('kind') not in ('packet','frame','stage','end'):raise ValueError('CDR record kind')
        payload=body[4+length:]
        if meta['kind']!='packet' and payload:raise ValueError('CDR metadata record payload')
        if meta['kind']=='end':
            if meta.get('records')!=sequence-1 or source.read(1):raise ValueError('CDR footer count/trailing bytes')
            yield dict(meta=meta,payload=payload)
            return
        yield dict(meta=meta,payload=payload)


def _message_types():
    from geometry_msgs.msg import PoseStamped
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import JointState,Imu,LaserScan
    from std_msgs.msg import String
    from tf2_msgs.msg import TFMessage
    from integrated_robot_interfaces.msg import MotionState,FootContacts
    result=dict(joints=JointState,applied_reference=JointState,imu=Imu,scan=LaserScan,body=Odometry,
        contacts=FootContacts,carry=MotionState,native_com=PoseStamped,
        native_controls=String,tf=TFMessage,tf_static=TFMessage)
    result.update({key+'_state':MotionState for key in ('crawl','carry','guard','startup')})
    return result


class ReplayState:
    """Reuse the legacy normalizer, inbox, and frame selection without ROS handles."""
    from probe_navigation_13_5 import NavigationProbe as _Probe
    _sensor=_Probe._sensor
    _body_source=_Probe._body_source
    _controls=_Probe._controls
    _com=_Probe._com
    _motion=_Probe._motion
    _tf=_Probe._tf
    _frame_at=_Probe._frame_at

    def __init__(self,engine,output):
        from integrated_robot_navigation.observations import SensorInbox
        self.engine=engine;self.output=output;self._lock=RLock();self.inbox=SensorInbox(0)
        self.native_com=None;self.com_pending={};self.motion={};self.stage='bootstrap'
        self.errors=[];self.transport_errors=[];self.tf_api={};self.missing=Counter()
        self.bounded_history=True
        self.frames=deque(maxlen=128);self.native_controls=deque(maxlen=128)
        self.body_references=deque(maxlen=128);self.transforms=deque(maxlen=128)
        self.values=dict(frames=[],native_controls=[],body_references=[],transforms=[])
        self.counts=Counter()

    def _write(self,kind,value):
        from split_observer_13_5 import _STREAMS
        encoded=json.dumps(dict(kind=kind,value=value),allow_nan=False)+'\n'
        self.output.write(encoded);self.counts[kind]+=1
        if kind in _STREAMS:self.values[_STREAMS[kind]].append(value)


def replay_recording(root,report):
    from rclpy.serialization import deserialize_message
    root=Path(root);types=_message_types()
    if report['engine']=='mujoco':
        from mujoco_ros2_control_msgs.msg import FreeJointStateArray
        types['body_source']=FreeJointStateArray
    output=root/'observations.jsonl';temporary=root/'observations.jsonl.tmp'
    if output.exists() or temporary.exists():raise ValueError('CDR replay output already exists')
    prefixes=deque(maxlen=128);max_receipt=0;count=0
    with temporary.open('x',encoding='utf-8') as target,(root/'observations.cdr').open('rb') as source:
        state=ReplayState(report['engine'],target)
        for row in read_records(source):
            meta,payload=row['meta'],row['payload'];count+=1;kind=meta['kind']
            if kind=='packet':
                receipt=meta.get('received_ns')
                if type(receipt) is not int or receipt<0:raise ValueError('CDR receipt metadata')
                max_receipt=max(max_receipt,receipt);key=meta['key'];state.stage=meta['stage']
                try:message=deserialize_message(payload,types[key])
                except Exception as error:raise ValueError('CDR message decode: '+key) from error
                info=dict(source_timestamp=meta['source_system_ns'],received_timestamp=meta['rmw_received_system_ns'],
                    publisher_gid=bytes.fromhex(meta['gid']))
                kwargs=dict(receipt_ns=receipt,system_ns=meta['callback_system_ns'])
                if key in state.inbox.pending:state._sensor(key,message,info,**kwargs)
                elif key=='body_source':state._body_source(message,info,**kwargs)
                elif key=='native_controls':state._controls(message,info,**kwargs)
                elif key=='native_com':state._com(message,receipt_ns=receipt)
                elif key=='applied_reference':
                    from probe_navigation_13_5 import transport_receipt
                    stamp=message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec
                    state._write('applied_reference',dict(stamp_ns=stamp,received_ns=receipt,
                        frame_id=message.header.frame_id,data=dict(name=list(message.name),position=list(message.position)),
                        scope='independent_observer_receipt_not_controller_receipt_or_credit',
                        transport=transport_receipt(stamp,receipt,meta['callback_system_ns'],info)))
                elif key.endswith('_state'):state._motion(key[:-6],message,receipt_ns=receipt)
                elif key in ('tf','tf_static'):state._tf(message,info)
                else:raise ValueError('CDR topic key')
            elif kind=='frame':
                if max_receipt>meta['wall_ns']:raise ValueError('CDR frame prefix received after cutoff')
                state.stage=meta['stage'];state._frame_at(meta['ros_ns'],meta['wall_ns'])
                prefixes.append(dict(sequence=meta['sequence'],ros_ns=meta['ros_ns'],wall_ns=meta['wall_ns'],
                    samples={key:asdict(value) if value else None for key,value in state.inbox.samples.items()}))
        if count!=report['records']:raise ValueError('CDR report record count')
    temporary.rename(output)
    return dict(**state.values,errors=state.errors,transport_errors=state.transport_errors,
        tf_api=state.tf_api,selected_prefixes=list(prefixes),missing=dict(state.missing),counts=dict(state.counts))


class NativeObserverProcess:
    """Same stage/finish boundary as the legacy observer; no capture IPC."""
    def __init__(self,directory,*,engine):
        import os
        import subprocess
        import time
        from ament_index_python.packages import get_package_prefix
        from split_observer_13_5 import _digest,_modules
        self.root=Path(directory).resolve(strict=True);self.engine=engine
        self.finished=False;self.joined=False;self.error=None;self.runtime_fault=None
        self.ipc_requests=0;self.data=None;self.result={};self.stop_sent=False;self._buffer=b'';self._lines=deque()
        prefix=Path(get_package_prefix('integrated_robot_navigation_sensors')).resolve(strict=True)
        binary=(prefix/'lib/integrated_robot_navigation_sensors/navigation_evidence_recorder').resolve(strict=True)
        if not binary.is_relative_to(prefix):raise RuntimeError('native observer executable outside selected prefix')
        self.stderr=(self.root/'native_observer.stderr.log').open('xb')
        requested=time.monotonic_ns()
        command=[str(binary),str(self.root/'observations.cdr'),engine]
        # This is a lifecycle log containing a byte-exact stderr payload. A
        # successful child may emit zero stderr bytes; record that observation
        # explicitly without weakening the shared nonempty-artifact contract.
        header=(json.dumps(dict(event='stderr_capture_open',command=command,
            executable_sha256=_digest(binary),requested_wall_ns=requested))+'\n').encode()
        self.stderr.write(header);self.stderr.flush();self.stderr_header_size=len(header)
        env=dict(os.environ,RCUTILS_LOGGING_USE_STDOUT='0')
        try:
            self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=self.stderr,start_new_session=True,env=env)
        except BaseException:
            self.stderr.close()
            raise
        try:
            kind,identity=self._receive(30.)
            if kind!='ready' or identity['pid']!=self.process.pid or identity['uid']!=os.getuid():
                raise RuntimeError('native observer identity/readiness')
            received=time.monotonic_ns()
            if not requested<=identity['node_ready_wall_ns']<=received:
                raise RuntimeError('native receipt clock differs from local MONOTONIC domain')
            stat=Path('/proc/'+str(self.process.pid)+'/stat').read_text().rsplit(')',1)[1].split()
            self.identity=dict(identity,pgid=os.getpgid(self.process.pid),start_ticks=int(stat[19]),
                executable=str(binary),executable_sha256=_digest(binary),
                source_manifest_sha256=_digest(prefix/'share/integrated_robot_navigation_sensors/source_manifest.json'),
                module_files=_modules(),spawn_requested_wall_ns=requested,parent_ready_received_wall_ns=received)
            (self.root/'observer_startup.json').write_text(json.dumps(self.identity,indent=2))
        except BaseException:
            self.finish(timeout_sec=20.)
            raise

    def _read_available(self,seconds):
        import os
        import select
        if not select.select([self.process.stdout],[],[],seconds)[0]:return False
        block=os.read(self.process.stdout.fileno(),65536)
        if not block:return False
        self._buffer+=block
        if len(self._buffer)>256*1024:raise RuntimeError('native observer IPC capacity')
        while b'\n' in self._buffer:
            line,self._buffer=self._buffer.split(b'\n',1)
            self._lines.append(json.loads(line))
        return True

    def _receive(self,seconds):
        import time
        deadline=time.monotonic()+seconds
        while not self._lines:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not self._read_available(remaining):raise RuntimeError('native observer response deadline/EOF')
        value=self._lines.popleft()
        if not isinstance(value,list) or len(value)!=2:raise RuntimeError('native observer IPC shape')
        return value

    def _notice(self,kind,value):
        if kind=='fault':self.runtime_fault=value
        elif kind=='closed':self.result=value
        else:
            self.error='native observer '+kind+': '+str(value)
            raise RuntimeError(self.error)

    def check(self,*,allow_runtime_fault=False):
        if self.error:raise RuntimeError(self.error)
        while not self.finished and (self._lines or self._read_available(0.)):
            self._notice(*self._lines.popleft())
        if not self.finished and self.process.poll() is not None:
            raise RuntimeError('native observer exited before finish')
        if self.runtime_fault and not allow_runtime_fault:raise RuntimeError('observer runtime fault: '+str(self.runtime_fault))

    def _request(self,kind,value=None,*,allow_runtime_fault=False):
        import time
        self.check(allow_runtime_fault=allow_runtime_fault)
        self.process.stdin.write((json.dumps([kind,value])+'\n').encode());self.process.stdin.flush()
        self.ipc_requests+=1;deadline=time.monotonic()+3.
        while True:
            reply,data=self._receive(max(0.,deadline-time.monotonic()))
            if reply==kind:
                if self.runtime_fault and not allow_runtime_fault:
                    raise RuntimeError('observer runtime fault: '+str(self.runtime_fault))
                return data
            self._notice(reply,data)

    def set_stage(self,stage):
        if self._request('stage',stage,allow_runtime_fault=stage=='shutdown')!=stage:
            raise RuntimeError('native observer stage acknowledgement mismatch')

    def transforms(self):return self._request('transforms')

    def finish(self,*,timeout_sec):
        import os
        import subprocess
        import time
        from split_observer_13_5 import _digest
        if self.finished:
            if self.error:raise RuntimeError(self.error)
            return self.data
        if not self.stop_sent:
            if self.process.poll() is None:
                try:
                    self.process.stdin.write(b'["stop",null]\n');self.process.stdin.flush();self.ipc_requests+=1
                except (OSError,ValueError):pass
            self.stop_sent=True
        try:self.process.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:raise RuntimeError('native observer process not joined; resources retained') from None
        self.joined=True
        while self._lines or self._read_available(0.):
            kind,value=self._lines.popleft()
            if kind=='error':self.error='native observer error: '+str(value)
            else:self._notice(kind,value)
        self.finished=True
        payload_size=os.fstat(self.stderr.fileno()).st_size-self.stderr_header_size
        if payload_size:self.stderr.write(b'\n')
        footer=dict(event='stderr_capture_closed',pid=self.process.pid,returncode=self.process.returncode,
            closed_wall_ns=time.monotonic_ns(),native_stderr_offset=self.stderr_header_size,
            native_stderr_bytes=payload_size)
        self.stderr.write((json.dumps(footer)+'\n').encode());self.stderr.close()
        self.process.stdin.close();self.process.stdout.close()
        self.runtime_fault=self.runtime_fault or self.result.get('runtime_fault')
        try:
            journal=self.result.get('journal',{})
            if (self.process.returncode!=0 or self.result.get('failure') or not self.result.get('ros_closed')
                    or not self.result.get('receiver',{}).get('closed') or not journal.get('joined')
                    or journal.get('error') or journal.get('submitted')!=journal.get('written')):
                raise RuntimeError('native observer close/result not confirmed: '+str(self.result))
            native=json.loads((self.root/'observer_native_report.json').read_text())
            if native!=self.result:raise RuntimeError('native observer IPC/file closure report differs')
            raw=self.root/'observations.cdr'
            recording=dict(engine=self.engine,records=journal['written'],raw_sha256=_digest(raw),
                raw_size=raw.stat().st_size,scope='original_cdr_original_native_receipt_complete_prefix_replay')
            self.result['recording']=recording
            self.data=replay_recording(self.root,recording)
            # The live file is closed. No future message can change this original.
            if _digest(raw)!=recording['raw_sha256']:raise RuntimeError('native observer original hash changed during replay')
            recording['json_sha256']=_digest(self.root/'observations.jsonl')
        except BaseException as error:
            self.error=repr(error)
        finally:
            self.result.update(identity=getattr(self,'identity',{}))
            (self.root/'observer_process_report.json').write_text(json.dumps(self.report(),indent=2,allow_nan=False))
        if self.error:raise RuntimeError(self.error)
        return self.data

    def report(self):
        return dict(self.result,joined=self.joined,exitcode=self.process.poll(),ipc_requests=self.ipc_requests,
            error=self.error,runtime_fault=self.runtime_fault)
