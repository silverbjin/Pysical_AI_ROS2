#!/usr/bin/env python3
"""Read-only native observations plus explicit services to the existing owners."""
from dataclasses import asdict
from collections import Counter, deque
import gc
import json
from threading import Condition, Event, RLock, Thread
import time

from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState, Imu, LaserScan
from std_srvs.srv import Trigger
from std_msgs.msg import String
from lifecycle_msgs.srv import ChangeState
from tf2_msgs.msg import TFMessage
from integrated_robot_interfaces.msg import MotionState, FootContacts
from integrated_robot_interfaces.srv import SetMode
from integrated_robot_navigation.observations import SensorInbox, sensor_sample
from integrated_robot_navigation.samples import Sample
from integrated_robot_navigation.dispatch_node import NavigationNode,make_navigation_executor
from observation_records_13_5 import freeze_sample, sample_record, json_value


def transport_receipt(stamp_ns, received_ns, system_ns, info):
    def field(name):
        value = info.get(name) if isinstance(info, dict) else getattr(info, name, None)
        return value if type(value) is int and value > 0 else None
    return dict(stamp_ns=stamp_ns, received_ns=received_ns, callback_system_ns=system_ns,
                source_system_ns=field('source_timestamp'),
                rmw_received_system_ns=field('received_timestamp'))


class JournalFailure(RuntimeError):
    """Acceptance failed; keep the independent cleanup RPC receiver alive."""


class EvidenceJournal:
    """One file owner; bounded immutable submissions, sticky failure, no drop."""
    def __init__(self, sink, *, max_records=256, max_bytes=8*1024*1024):
        if type(max_records) is not int or type(max_bytes) is not int or min(max_records,max_bytes)<=0:
            raise ValueError('positive journal capacity required')
        self.sink=sink;self.max_records=max_records;self.max_bytes=max_bytes
        self.condition=Condition();self.pending=deque();self.accepting=True;self.error=None
        self.submitted=self.written=self.outstanding_bytes=self.outstanding_records=0
        self.peak_bytes=self.peak_records=self.write_wall_ns=self.max_write_wall_ns=0
        self.write_cpu_ns=0
        self.thread=Thread(target=self._run,name='navigation_evidence_journal')
        self.thread.start()

    def _check(self):
        if self.error is not None:raise JournalFailure('observation journal failed: '+self.error)

    def submit(self, encoded):
        if type(encoded) is not str:raise TypeError('immutable encoded journal text required')
        size=len(encoded.encode('utf-8'))
        with self.condition:
            self._check()
            if not self.accepting:raise RuntimeError('observation journal closed')
            if self.outstanding_records>=self.max_records or self.outstanding_bytes+size>self.max_bytes:
                self.error='journal capacity exceeded';self.accepting=False
                self.condition.notify_all();self._check()
            self.pending.append((encoded,size));self.submitted+=1
            self.outstanding_records+=1;self.outstanding_bytes+=size
            self.peak_records=max(self.peak_records,self.outstanding_records)
            self.peak_bytes=max(self.peak_bytes,self.outstanding_bytes)
            self.condition.notify_all()

    def _run(self):
        try:
            while True:
                with self.condition:
                    while not self.pending and self.accepting:self.condition.wait()
                    if not self.pending:break
                    encoded,size=self.pending.popleft()
                start,cpu=time.monotonic_ns(),time.thread_time_ns()
                count=self.sink.write(encoded)
                end,used=time.monotonic_ns(),time.thread_time_ns()-cpu
                if count!=len(encoded):raise OSError('short observation journal write')
                with self.condition:
                    self.written+=1;self.outstanding_records-=1;self.outstanding_bytes-=size
                    self.write_wall_ns+=end-start;self.write_cpu_ns+=used
                    self.max_write_wall_ns=max(self.max_write_wall_ns,end-start)
                    self.condition.notify_all()
            self.sink.flush()
        except BaseException as error:
            with self.condition:
                self.error=self.error or repr(error);self.accepting=False;self.condition.notify_all()
        finally:
            try:self.sink.close()
            except BaseException as error:
                with self.condition:self.error=self.error or repr(error)
            with self.condition:self.condition.notify_all()

    def flush(self, *, timeout_sec=5.):
        # Test/teardown barrier only. Live callbacks only submit, never wait.
        deadline=time.monotonic()+timeout_sec
        with self.condition:
            target=self.submitted
            while self.written<target:
                self._check();remaining=deadline-time.monotonic()
                if remaining<=0:raise RuntimeError('journal flush not confirmed')
                self.condition.wait(remaining)
            self._check()
        # No concurrent sink write remains at this barrier (caller owns ingress).
        if not self.sink.closed:self.sink.flush()

    def close(self, *, timeout_sec=5.):
        with self.condition:self.accepting=False;self.condition.notify_all()
        self.thread.join(timeout_sec)
        if self.thread.is_alive():raise RuntimeError('observation journal worker not joined')
        with self.condition:
            self._check()
            if self.written!=self.submitted:raise RuntimeError('observation journal count mismatch')

    def report(self):
        with self.condition:
            return dict(scope='actual_file_writer_not_ingress_enqueue',submitted=self.submitted,
                written=self.written,outstanding_records=self.outstanding_records,
                outstanding_bytes=self.outstanding_bytes,max_records=self.max_records,max_bytes=self.max_bytes,
                peak_records=self.peak_records,peak_bytes=self.peak_bytes,error=self.error,
                accepting=self.accepting,joined=not self.thread.is_alive(),write_wall_ns=self.write_wall_ns,
                write_cpu_ns=self.write_cpu_ns,max_write_wall_ns=self.max_write_wall_ns)


class RecordingNode(NavigationNode):
    def make_receiver_executor(self):
        return make_navigation_executor(self)


class ProbeReceiver:
    """One owned callback executor, independent of caller IO/graph/proc scans."""
    def __init__(self, node):
        if node.executor is not None:
            raise ValueError('probe already has an executor owner')
        self.stopping, self.closed, self.error = Event(), False, None
        factory=getattr(node,'make_receiver_executor',None)
        self.executor = factory() if factory is not None else SingleThreadedExecutor(context=node.context)
        self.node = node
        self.recording_receiver = self.ingress_receiver = None
        self.thread = Thread(target=self._spin, name='navigation_probe_receiver')
        try:
            self.executor.add_node(node)
            if getattr(node,'recording_node',None) is not None:
                self.recording_receiver=ProbeReceiver(node.recording_node)
            if getattr(node,'ingress_node',None) is not None:
                self.ingress_receiver=ProbeReceiver(node.ingress_node)
            self.thread.start()  # last: a constructor failure cannot orphan it
        except BaseException:
            for child in (self.recording_receiver,self.ingress_receiver):
                if child is not None and not child.shutdown(timeout_sec=2.):
                    raise RuntimeError('child receiver not joined after construction failure')
            self.executor.shutdown(timeout_sec=2.)
            raise

    def _spin(self):
        try:
            while not self.stopping.is_set() and self.node.context.ok():
                self.executor.spin_once(timeout_sec=.02)
        except BaseException as error:
            self.error = error  # sticky; the caller must fail, never restart it

    def check(self):
        if self.recording_receiver is not None:self.recording_receiver.check()
        if self.ingress_receiver is not None:self.ingress_receiver.check()
        if self.error is not None:
            raise RuntimeError('probe receiver callback failed: '+repr(self.error)) from self.error
        if not self.thread.is_alive() and not self.stopping.is_set():
            raise RuntimeError('probe receiver exited unexpectedly')

    def report(self):
        return dict(node=self.node.get_name(),thread_ident=self.thread.ident,
            thread_alive=self.thread.is_alive(),closed=self.closed,
            error=repr(self.error) if self.error is not None else None,
            recording=self.recording_receiver.report() if self.recording_receiver is not None else None,
            ingress=self.ingress_receiver.report() if self.ingress_receiver is not None else None)

    def shutdown(self, *, timeout_sec):
        if self.closed:
            return True
        deadline = time.monotonic()+timeout_sec
        self.stopping.set()
        self.executor.wake()
        for child in (self.recording_receiver,self.ingress_receiver):
            if child is not None:
                child.stopping.set()
                child.executor.wake()
        self.thread.join(timeout=max(0., deadline-time.monotonic()))
        if self.thread.is_alive():
            return False  # retain the executor/ROS handles until the callback ends
        for child in (self.recording_receiver,self.ingress_receiver):
            if child is not None and not child.shutdown(timeout_sec=max(0.,deadline-time.monotonic())):
                return False
        self.closed = bool(self.executor.shutdown(timeout_sec=max(0., deadline-time.monotonic())))
        return self.closed


class NavigationProbe(NavigationNode):
    def make_receiver_executor(self):
        # This role was already serial. Reuse the reviewed MessageInfo adapter
        # and official event loop; no callback-group parallelism is discarded.
        return make_navigation_executor(self)

    def __init__(self, directory, engine='mujoco', *, bounded_history=False, **kwargs):
        super().__init__('navigation_native_probe', parameter_overrides=[Parameter('use_sim_time', value=True)], **kwargs)
        self._lock = RLock()
        self._record_lock = RLock()
        # As in the established arm transport: no launch name/clock wildcard
        # inheritance. Only the parent owns a TimeSource subscription.
        self.recording_node=(RecordingNode('navigation_probe_recording',context=self.context,
            namespace=self.get_namespace(),use_global_arguments=False,
            parameter_overrides=[Parameter('use_sim_time',value=False)]) if bounded_history else None)
        # Native safety samples cannot queue behind 500Hz clock events or RPC
        # completions. This owner has no TimeSource subscription; the original
        # parent clock remains the only decision clock, with unchanged ages.
        self.ingress_node=(RecordingNode('navigation_probe_ingress',context=self.context,
            namespace=self.get_namespace(),use_global_arguments=False,
            parameter_overrides=[Parameter('use_sim_time',value=False)]) if bounded_history else None)
        recorder=self.recording_node if self.recording_node is not None else self
        ingress=self.ingress_node if self.ingress_node is not None else self
        self.inbox = SensorInbox(0)
        self.native_com, self.com_pending = None, {}
        self.motion = {}
        self.frames, self.errors, self.transforms = [], [], []
        self.tf_api = {}
        self.transport_errors = []
        self.engine, self.native_controls = engine, []
        self.body_references = []
        self.bounded_history = bounded_history
        self.journal_path = directory/'observations.jsonl'
        self.journal_counts = Counter()
        self.callback_costs,self.journal_costs={},{}
        self.journal_failure=None
        self.slow_callbacks=deque(maxlen=512)
        self.slow_callback_count=0
        self.history_restored = False
        self.gc_spans, self.gc_started = deque(maxlen=512), {}
        self.gc_observer = None
        if bounded_history:
            self.frames, self.native_controls = deque(maxlen=128), deque(maxlen=128)
            self.transforms, self.body_references = deque(maxlen=128), deque(maxlen=128)
        self.stage, self.ignore_faults = 'bootstrap', False
        self.missing = Counter()
        self.raw = (directory/'observations.jsonl').open('w', encoding='utf-8')
        self.journal = None
        qos = qos_profile_sensor_data
        for key, kind, topic in (
            ('joints', JointState, '/joint_states'), ('imu', Imu, '/navigation/imu'),
            ('contacts', FootContacts, '/navigation/foot_contacts'), ('body', Odometry, '/odom'),
            ('scan', LaserScan, '/scan'), ('carry', MotionState, '/navigation/carry_state')):
            ingress.create_subscription(kind, topic,
                lambda msg, info, stream=key: self._dispatch(self._sensor, stream, msg, info), qos)
        if engine == 'mujoco':
            from mujoco_ros2_control_msgs.msg import FreeJointStateArray
            ingress.create_subscription(FreeJointStateArray, '/native/free_joint_states',
                lambda msg, info: self._dispatch(self._body_source, msg, info), qos)
        # Both native MuJoCo and the installed Gazebo bridge offer RELIABLE.
        # Keep per-capture gyro references separate from best-effort sensors.
        recorder.create_subscription(String, '/navigation/native_controls',
            lambda msg, info: self._dispatch(self._controls, msg, info),
            QoSProfile(depth=100))
        ingress.create_subscription(PoseStamped, '/navigation/native_com',
            lambda msg: self._dispatch(self._com, msg), qos)
        for key in ('crawl', 'carry', 'guard', 'startup'):
            self.create_subscription(MotionState, '/navigation/'+key+'_state',
                                     lambda msg, stream=key: self._dispatch(self._motion, stream, msg), 10)
        recorder.create_subscription(TFMessage, '/tf', lambda msg, info: self._dispatch(self._tf, msg, info), qos,
            raw=bounded_history)
        recorder.create_subscription(TFMessage, '/tf_static', lambda msg, info: self._dispatch(self._tf, msg, info),
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL),raw=bounded_history)
        self.mode = self.create_client(SetMode, '/navigation/set_mode')
        self.calibrate = self.create_client(Trigger, '/crawl_controller/calibrate_contact')
        self.crawl_report = self.create_client(Trigger, '/crawl_controller/report')
        self.lifecycle = self.create_client(ChangeState, '/crawl_controller/change_state')
        self.carry_report = self.create_client(Trigger, '/carry_manager/report')
        self.carry_stop = self.create_client(Trigger, '/carry_manager/stop')
        self.native_stop = self.create_client(Trigger, '/navigation/stop_native_sensors')
        self.native_command_trace = self.create_client(Trigger, '/navigation/native_command_trace')
        self.control_clock_report = self.create_client(Trigger, '/navigation_control_clock/report')
        self.control_clock_stop = self.create_client(Trigger, '/navigation_control_clock/stop')
        recorder.create_timer(.02, lambda: self._dispatch(self._frame),clock=self.get_clock())
        if bounded_history:
            # Start only after all ROS construction succeeds. The writer owns
            # the file but never the inbox lock, ROS handles or command owner.
            self.journal=EvidenceJournal(self.raw)
            # Observe, never disable or tune the process GC policy. Installed
            # last so constructor failure cannot leak a global callback.
            self.gc_observer = self._gc_event
            gc.callbacks.append(self.gc_observer)

    def _gc_event(self, phase, info):
        generation = info['generation']
        if phase == 'start':
            self.gc_started[generation] = time.monotonic_ns()
        elif generation in self.gc_started:
            start = self.gc_started.pop(generation)
            end = time.monotonic_ns()
            if end-start >= 1_000_000:
                self.gc_spans.append(dict(generation=generation,started_wall_ns=start,
                    finished_wall_ns=end,duration_ms=(end-start)/1e6,
                    live_frames=len(self.frames),live_controls=len(self.native_controls)))

    def _stop_gc_observer(self):
        if self.gc_observer is not None:
            gc.callbacks.remove(self.gc_observer)
            self.gc_observer = None

    def restore_history(self, *, receiver_joined):
        """Only after native shutdown and callback join; assess the WHOLE journal."""
        if not receiver_joined:
            raise RuntimeError('probe receiver must be joined before restoring journal')
        if not self.bounded_history or self.history_restored:
            return
        self._stop_gc_observer()
        self.flush_log(final=True)
        streams = {key: [] for key in ('frame','native_controls','body_reference','tf_transform')}
        with self.journal_path.open(encoding='utf-8') as source:
            for line in source:
                row = json.loads(line)  # corrupt/truncated evidence must fail
                if row['kind'] in streams:
                    streams[row['kind']].append(row['value'])
        if any(len(rows) != self.journal_counts[key] for key,rows in streams.items()):
            raise RuntimeError('journal record count differs from live recording')
        report = dict(scope='all_journal_records_after_native_stop_and_receiver_join',
            counts=dict(self.journal_counts),live_cache_limit=128,
            live_lengths=dict(frames=len(self.frames),controls=len(self.native_controls),
                transforms=len(self.transforms),body_references=len(self.body_references)),
            gc_policy_changed=False,gc_spans=list(self.gc_spans),observer_timing=self.timing_snapshot())
        self.frames,self.native_controls = streams['frame'],streams['native_controls']
        self.body_references,self.transforms = streams['body_reference'],streams['tf_transform']
        self.history_restored = True
        with (self.journal_path.parent/'recording_report.json').open('x') as output:
            json.dump(report,output,indent=2,allow_nan=False)

    def _dispatch(self, callback, *args):
        started,cpu=time.monotonic_ns(),time.thread_time_ns()
        key=callback.__name__+(':'+args[0] if callback.__name__=='_sensor' else '')
        # The wrapper must not renew first receipt after waiting for the inbox.
        # Each callback captures entry time, normalizes outside the state lock,
        # replaces its private state briefly, then records outside that lock.
        try:callback(*args)
        except JournalFailure as error:
            # Keep cleanup RPCs alive, while acceptance remains sticky failed.
            with self._lock:
                if self.journal_failure is None:
                    self.journal_failure=dict(reason=str(error),callback=key,
                        ros_ns=self.get_clock().now().nanoseconds,wall_ns=time.monotonic_ns())
        finally:
            end=time.monotonic_ns();elapsed=end-started;used=time.thread_time_ns()-cpu
            with self._lock:
                row=self.callback_costs.setdefault(key,dict(count=0,wall_ns=0,cpu_ns=0,
                    lock_wait_ns=0,max_wall_ns=0,max_cpu_ns=0))
                row['count']+=1;row['wall_ns']+=elapsed;row['cpu_ns']+=used
                row['max_wall_ns']=max(row['max_wall_ns'],elapsed);row['max_cpu_ns']=max(row['max_cpu_ns'],used)
                if elapsed>=5_000_000:
                    self.slow_callback_count+=1
                    self.slow_callbacks.append(dict(callback=key,started_wall_ns=started,finished_wall_ns=end,
                        wall_ns=elapsed,cpu_ns=used,lock_wait_ns=0))

    def timing_snapshot(self):
        with self._lock,self._record_lock:
            return dict(scope='local_observer_cost_not_dds_queue_or_capture_latency',
                lock_wait_scope='dispatch_wrapper_only_no_wrapper_lock_callback_internal_wait_is_in_wall_cost',
                callbacks={key:dict(value) for key,value in self.callback_costs.items()},
                journal={key:dict(value) for key,value in self.journal_costs.items()},
                slow_threshold_ns=5_000_000,slow_seen=self.slow_callback_count,
                slow_retained=len(self.slow_callbacks),slow_discarded=self.slow_callback_count-len(self.slow_callbacks),
                slow_callbacks=[dict(value) for value in self.slow_callbacks],
                file_writer=self.journal.report() if getattr(self,'journal',None) is not None else None,
                journal_failure=getattr(self,'journal_failure',None),
                journal_write_scope='enqueue' if getattr(self,'journal',None) is not None else 'synchronous_file')

    def set_stage(self, stage, *, ignore_faults=None):
        with self._lock:
            self.stage = stage
            if ignore_faults is not None:
                self.ignore_faults = ignore_faults

    def transform_snapshot(self):
        with self._lock:
            return list(self.transforms)

    def _write(self, kind, value):
        if self.history_restored:
            raise RuntimeError('journal finalized; no callback may append')
        start,cpu=time.monotonic_ns(),time.thread_time_ns()
        encoded=json.dumps(dict(kind=kind,value=value),allow_nan=False,default=json_value)+'\n'
        serialized,serialized_cpu=time.monotonic_ns(),time.thread_time_ns()
        # Encoding must precede this short lock: otherwise a sensor callback
        # holding the inbox lock can wait indirectly on a heavy JSON encoder.
        with self._record_lock:
            if self.journal is not None:self.journal.submit(encoded)
            else:self.raw.write(encoded)
            end,end_cpu=time.monotonic_ns(),time.thread_time_ns()
            row=self.journal_costs.setdefault(kind,dict(count=0,encoded_bytes=0,serialize_wall_ns=0,
                serialize_cpu_ns=0,write_wall_ns=0,write_cpu_ns=0,max_serialize_wall_ns=0,max_write_wall_ns=0))
            row['count']+=1;row['encoded_bytes']+=len(encoded)
            row['serialize_wall_ns']+=serialized-start;row['serialize_cpu_ns']+=serialized_cpu-cpu
            row['write_wall_ns']+=end-serialized;row['write_cpu_ns']+=end_cpu-serialized_cpu
            row['max_serialize_wall_ns']=max(row['max_serialize_wall_ns'],serialized-start)
            row['max_write_wall_ns']=max(row['max_write_wall_ns'],end-serialized)
            if self.bounded_history and kind in ('frame','native_controls','body_reference','tf_transform'):
                self.journal_counts[kind] += 1

    def _sensor(self, key, msg, info=None):
        receipt = time.monotonic_ns()
        system_ns = time.time_ns() if key in ('body','scan') or (key == 'contacts' and self.bounded_history) else None
        try:
            value = sensor_sample(key, msg, receipt, 0)
            if self.bounded_history:value=freeze_sample(value)
            with self._lock:self.inbox.receive(key, value)
            self._write(key, sample_record(value) if self.bounded_history else asdict(value))
            if key == 'contacts' and self.bounded_history and info is not None:
                self._write('contacts_transport', dict(
                    **transport_receipt(value.stamp_ns, receipt, system_ns, info),
                    native_sequence=int(msg.sequence),epoch=int(msg.epoch)))
            if key == 'scan':
                self._write('scan_transport',transport_receipt(value.stamp_ns,receipt,system_ns,info))
            if key == 'body':
                self._write('body_transport', transport_receipt(value.stamp_ns, receipt, system_ns, info))
                if self.engine == 'gazebo':
                    reference = dict(capture_ns=value.stamp_ns,epoch=value.epoch,
                        sequence=value.sequence,frame_id=value.data['child_frame_id'],
                        source='gazebo_native_odometry',
                        angular_velocity=list(value.data['angular_velocity']))
                    if self.bounded_history:self._write('body_reference',reference)
                    with self._lock:
                        if len(self.body_references) >= 20000:
                            raise ValueError('native body reference capacity')
                        self.body_references.append(reference)
        except (ValueError, TypeError) as error:
            with self._lock:self.errors.append(key+':'+str(error))

    def _body_source(self, msg, info):
        receipt, system_ns = time.monotonic_ns(), time.time_ns()
        states = [state for state in msg.free_joints if state.name == 'base_link']
        if len(states) != 1 or states[0].pose.header.frame_id != '':
            with self._lock:self.transport_errors.append('native body source shape/frame')
            return
        stamp = states[0].pose.header.stamp
        self._write('body_source', transport_receipt(
            stamp.sec*1_000_000_000+stamp.nanosec, receipt, system_ns, info))

    def _controls(self, msg, info=None):
        receipt = time.monotonic_ns()
        with self._lock:stage=self.stage
        system_ns = time.time_ns() if info is not None and self.bounded_history else None
        try:
            value = json.loads(msg.data)
            schema = (isinstance(value, dict) and (
                self.engine == 'mujoco' and value.get('schema') == 1
                and isinstance(value.get('actuators'), list) or
                self.engine == 'gazebo' and value.get('schema') == 2
                and value.get('engine') == 'gazebo' and isinstance(value.get('joints'), list)))
            if (not schema
                    or any(type(value.get(key)) is not int or value[key] < 0
                           for key in ('capture_ns', 'epoch', 'sequence'))):
                raise ValueError('native controls diagnostic schema')
            with self._lock:
                if len(self.native_controls) >= 20000:
                    raise ValueError('native controls diagnostic capacity')
            value.update(received_ns=receipt, stage=stage)
            self._write('native_controls', value)
            if info is not None and self.bounded_history:
                self._write('native_controls_transport', dict(
                    **transport_receipt(value['capture_ns'],receipt,system_ns,info),
                    native_sequence=value['sequence'],epoch=value['epoch']))
            with self._lock:self.native_controls.append(value)
        except (ValueError, TypeError) as error:
            with self._lock:self.transport_errors.append('native_controls:'+str(error))

    def _com(self, msg):
        receipt=time.monotonic_ns()
        stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        p = msg.pose.position
        value=Sample(stamp,receipt,0,stamp,msg.header.frame_id,(p.x,p.y,p.z))
        with self._lock:
            if self.native_com is None or stamp > self.native_com.stamp_ns:
                self.com_pending.setdefault(stamp,value)
            while len(self.com_pending) > 10:
                del self.com_pending[min(self.com_pending)]

    def _motion(self, key, msg):
        value = dict(state=msg.state, phase=msg.phase, swing_foot=msg.swing_foot,
                     generation=msg.generation, model_sha256=msg.model_sha256,
                     ready=msg.ready, stopped=msg.stopped, fault_reason=msg.fault_reason,
                     stamp_ns=msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec,
                     received_ns=time.monotonic_ns())
        with self._lock:self.motion[key] = value
        self._write(key+'_state', value)

    def _tf(self, msg, info):
        try:
            raw_gid = info.get('publisher_gid') if isinstance(info, dict) else getattr(info, 'publisher_gid', None)
            if (raw_gid is None and isinstance(info, dict)
                    and type(info.get('source_timestamp')) is int
                    and type(info.get('received_timestamp')) is int):
                with self._lock:
                    self.tf_api = dict(publisher_gid_available=False,
                                      authority_source='required_native_cpp_observer')
                return  # this API capability is not a native runtime fault
            gid_bytes = bytes(raw_gid) if raw_gid is not None else b''
            if not gid_bytes:
                raise ValueError('missing publisher_gid')
            gid = gid_bytes.hex()
        except (ValueError, TypeError) as error:
            with self._lock:self.errors.append('tf_metadata:'+str(error))
            return  # retain a usable executor for explicit owner/engine cleanup
        # Jazzy's event metadata may lack publisher_gid. Check that capability
        # before expanding every transform into Python objects. Native C++
        # authority verification remains mandatory; never invent an identity.
        if isinstance(msg,bytes):
            try:msg=deserialize_message(msg,TFMessage)
            except Exception as error:
                with self._lock:self.errors.append('tf_serialization:'+repr(error))
                return
        for transform in msg.transforms:
            reference = dict(parent=transform.header.frame_id,
                child=transform.child_frame_id, gid=gid,
                stamp_ns=transform.header.stamp.sec*1_000_000_000+transform.header.stamp.nanosec)
            if self.bounded_history:self._write('tf_transform',reference)
            with self._lock:self.transforms.append(reference)

    def _frame(self):
        with self._lock:
            ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
            captured = self.inbox.bundle(ros_ns)
            eligible = [stamp for stamp in self.com_pending if stamp <= ros_ns]
            if eligible:
                latest = max(eligible)
                self.native_com = self.com_pending[latest]
                for stamp in list(self.com_pending):
                    if stamp <= latest:
                        del self.com_pending[stamp]
            com,stage,crawl=self.native_com,self.stage,dict(self.motion.get('crawl', {}))
        # Bounded observations own immutable values frozen once at admission.
        # Reuse those values; later ingress cannot change this capture snapshot.
        samples=({key:sample_record(getattr(captured,key)) for key in
            ('joints','imu','contacts','body','scan','carry')}
            if self.bounded_history else asdict(captured))
        samples['native_com']=sample_record(com) if self.bounded_history else (asdict(com) if com else None)
        absent=[key for key,value in samples.items() if value is None]
        if absent:
            with self._lock:self.missing.update(absent)
            return
        row=dict(ros_ns=ros_ns,wall_ns=wall_ns,stage=stage,samples=samples,crawl=crawl)
        with self._lock:self.frames.append(row)
        self._write('frame', row)

    def fault(self):
        with self._lock:
            if self.journal is not None:
                report=self.journal.report()
                if report['error']:return 'observation journal:'+report['error']
            faults = [key+':'+value['fault_reason'] for key, value in self.motion.items() if value['fault_reason']]
            return (self.errors+faults)[0] if self.errors or faults else ''

    def latest_frame(self):
        # _frame appends a fresh record and never mutates that row.
        with self._lock:return self.frames[-1] if self.frames else None

    def movement_decision(self, limits):
        """Select native ingress at one decision, independently of journal timer.

        A recorded frame remains immutable evidence of its original decision;
        rechecking it at a later clock can expire it after fresher ingress has
        already arrived. Select under the inbox lock, never renew either age.
        """
        from integrated_robot_navigation.g2_sequence import movement_snapshot
        with self._lock:
            ros_ns,wall_ns=self.get_clock().now().nanoseconds,time.monotonic_ns()
            bundle=self.inbox.bundle(ros_ns,wall_ns=wall_ns)
            stage,crawl=self.stage,dict(self.motion.get('crawl',{}))
        # Private normalized samples are immutable after admission. Projection,
        # deep copies and evidence cannot own the native ingress mutex.
        row=dict(ros_ns=ros_ns,wall_ns=wall_ns,stage=stage,
            samples={key:(sample_record(getattr(bundle,key)) if getattr(self,'bounded_history',False)
                else asdict(getattr(bundle,key)) if getattr(bundle,key) is not None else None)
                for key in ('body','contacts')},crawl=crawl)
        try:
            value=movement_snapshot(row,ros_ns,wall_ns,limits)
        except (ValueError,TypeError) as error:
            self._write('movement_decision',dict(row,accepted=False,error=str(error),
                observer_timing=self.timing_snapshot()))
            raise
        self._write('movement_decision',dict(row,accepted=True))
        return value

    def owner_graph(self,*,include_command_sources=False):
        topics = ('/clock', '/joint_states', '/odom', '/navigation/odom', '/scan', '/navigation/imu',
                  '/navigation/foot_contacts', '/navigation/native_com', '/navigation/carry_state',
                  '/leg_position_controller/commands', '/gripper_position_controller/commands',
                  '/navigation/cmd_vel')
        topics += ('/navigation/native_controls',)
        if include_command_sources:
            topics+=('/navigation/cmd_vel_raw','/navigation/cmd_vel_smoothed')
        return {topic: [dict(node=value.node_namespace+'/'+value.node_name,
                            gid=bytes(value.endpoint_gid).hex())
                        for value in self.get_publishers_info_by_topic(topic)] for topic in topics}

    def close_log(self):
        self._stop_gc_observer()
        self.flush_log(final=True)

    def flush_log(self, *, final=False):
        if self.journal is not None:
            if final:self.journal.close()
            else:self.journal.flush()
        elif not self.raw.closed:
            self.raw.flush()
            if final:self.raw.close()

    def destroy_node(self):
        if self.ingress_node is not None:
            self.ingress_node.destroy_node()
            self.ingress_node=None
        if self.recording_node is not None:
            self.recording_node.destroy_node()
            self.recording_node=None
        return super().destroy_node()
