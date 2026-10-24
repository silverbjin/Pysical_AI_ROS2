#!/usr/bin/env python3
"""Read-only native observations plus explicit services to the existing owners."""
from dataclasses import asdict
from collections import Counter
import json
from threading import Event, RLock, Thread
import time

from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
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


def transport_receipt(stamp_ns, received_ns, system_ns, info):
    def field(name):
        value = info.get(name) if isinstance(info, dict) else getattr(info, name, None)
        return value if type(value) is int and value > 0 else None
    return dict(stamp_ns=stamp_ns, received_ns=received_ns, callback_system_ns=system_ns,
                source_system_ns=field('source_timestamp'),
                rmw_received_system_ns=field('received_timestamp'))


class ProbeReceiver:
    """One owned callback executor, independent of caller IO/graph/proc scans."""
    def __init__(self, node):
        if node.executor is not None:
            raise ValueError('probe already has an executor owner')
        self.stopping, self.closed, self.error = Event(), False, None
        self.executor = SingleThreadedExecutor(context=node.context)
        self.node = node
        self.thread = Thread(target=self._spin, name='navigation_probe_receiver')
        try:
            self.executor.add_node(node)
            self.thread.start()  # last: a constructor failure cannot orphan it
        except BaseException:
            self.executor.shutdown(timeout_sec=2.)
            raise

    def _spin(self):
        try:
            while not self.stopping.is_set() and self.node.context.ok():
                self.executor.spin_once(timeout_sec=.02)
        except BaseException as error:
            self.error = error  # sticky; the caller must fail, never restart it

    def check(self):
        if self.error is not None:
            raise RuntimeError('probe receiver callback failed: '+repr(self.error)) from self.error
        if not self.thread.is_alive() and not self.stopping.is_set():
            raise RuntimeError('probe receiver exited unexpectedly')

    def shutdown(self, *, timeout_sec):
        if self.closed:
            return True
        deadline = time.monotonic()+timeout_sec
        self.stopping.set()
        self.executor.wake()
        self.thread.join(timeout=max(0., deadline-time.monotonic()))
        if self.thread.is_alive():
            return False  # retain the executor/ROS handles until the callback ends
        self.closed = bool(self.executor.shutdown(timeout_sec=max(0., deadline-time.monotonic())))
        return self.closed


class NavigationProbe(Node):
    def __init__(self, directory, engine='mujoco', **kwargs):
        super().__init__('navigation_native_probe', parameter_overrides=[Parameter('use_sim_time', value=True)], **kwargs)
        self._lock = RLock()
        self.inbox = SensorInbox(0)
        self.native_com, self.com_pending = None, {}
        self.motion = {}
        self.frames, self.errors, self.transforms = [], [], []
        self.tf_api = {}
        self.transport_errors = []
        self.engine, self.native_controls = engine, []
        self.body_references = []
        self.stage, self.ignore_faults = 'bootstrap', False
        self.missing = Counter()
        self.raw = (directory/'observations.jsonl').open('w', encoding='utf-8')
        qos = qos_profile_sensor_data
        for key, kind, topic in (
            ('joints', JointState, '/joint_states'), ('imu', Imu, '/navigation/imu'),
            ('contacts', FootContacts, '/navigation/foot_contacts'), ('body', Odometry, '/odom'),
            ('scan', LaserScan, '/scan'), ('carry', MotionState, '/navigation/carry_state')):
            self.create_subscription(kind, topic,
                lambda msg, info, stream=key: self._dispatch(self._sensor, stream, msg, info), qos)
        if engine == 'mujoco':
            from mujoco_ros2_control_msgs.msg import FreeJointStateArray
            self.create_subscription(FreeJointStateArray, '/native/free_joint_states',
                lambda msg, info: self._dispatch(self._body_source, msg, info), qos)
        self.create_subscription(String, '/navigation/native_controls',
            lambda msg: self._dispatch(self._controls, msg),
            QoSProfile(depth=100) if engine == 'mujoco' else qos)
        self.create_subscription(PoseStamped, '/navigation/native_com',
            lambda msg: self._dispatch(self._com, msg), qos)
        for key in ('crawl', 'carry', 'guard', 'startup'):
            self.create_subscription(MotionState, '/navigation/'+key+'_state',
                                     lambda msg, stream=key: self._dispatch(self._motion, stream, msg), 10)
        self.create_subscription(TFMessage, '/tf', lambda msg, info: self._dispatch(self._tf, msg, info), qos)
        self.create_subscription(TFMessage, '/tf_static', lambda msg, info: self._dispatch(self._tf, msg, info),
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.mode = self.create_client(SetMode, '/navigation/set_mode')
        self.calibrate = self.create_client(Trigger, '/crawl_controller/calibrate_contact')
        self.crawl_report = self.create_client(Trigger, '/crawl_controller/report')
        self.lifecycle = self.create_client(ChangeState, '/crawl_controller/change_state')
        self.carry_report = self.create_client(Trigger, '/carry_manager/report')
        self.carry_stop = self.create_client(Trigger, '/carry_manager/stop')
        self.native_stop = self.create_client(Trigger, '/navigation/stop_native_sensors')
        self.create_timer(.02, lambda: self._dispatch(self._frame))

    def _dispatch(self, callback, *args):
        with self._lock:
            callback(*args)

    def set_stage(self, stage, *, ignore_faults=None):
        with self._lock:
            self.stage = stage
            if ignore_faults is not None:
                self.ignore_faults = ignore_faults

    def transform_snapshot(self):
        with self._lock:
            return list(self.transforms)

    def _write(self, kind, value):
        self.raw.write(json.dumps(dict(kind=kind, value=value), allow_nan=False)+'\n')

    def _sensor(self, key, msg, info=None):
        receipt = time.monotonic_ns()
        system_ns = time.time_ns() if key == 'body' else None
        try:
            value = sensor_sample(key, msg, receipt, 0)
            self.inbox.receive(key, value)
            self._write(key, asdict(value))
            if key == 'body':
                self._write('body_transport', transport_receipt(value.stamp_ns, receipt, system_ns, info))
                if self.engine == 'gazebo':
                    if len(self.body_references) >= 20000:
                        raise ValueError('native body reference capacity')
                    self.body_references.append(dict(capture_ns=value.stamp_ns,epoch=value.epoch,
                        sequence=value.sequence,frame_id=value.data['child_frame_id'],
                        source='gazebo_native_odometry',
                        angular_velocity=list(value.data['angular_velocity'])))
        except (ValueError, TypeError) as error:
            self.errors.append(key+':'+str(error))

    def _body_source(self, msg, info):
        receipt, system_ns = time.monotonic_ns(), time.time_ns()
        states = [state for state in msg.free_joints if state.name == 'base_link']
        if len(states) != 1 or states[0].pose.header.frame_id != '':
            self.transport_errors.append('native body source shape/frame')
            return
        stamp = states[0].pose.header.stamp
        self._write('body_source', transport_receipt(
            stamp.sec*1_000_000_000+stamp.nanosec, receipt, system_ns, info))

    def _controls(self, msg):
        receipt = time.monotonic_ns()
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
            if len(self.native_controls) >= 20000:
                raise ValueError('native controls diagnostic capacity')
            value.update(received_ns=receipt, stage=self.stage)
            self._write('native_controls', value)
            self.native_controls.append(value)
        except (ValueError, TypeError) as error:
            self.transport_errors.append('native_controls:'+str(error))

    def _com(self, msg):
        stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        p = msg.pose.position
        if self.native_com is None or stamp > self.native_com.stamp_ns:
            self.com_pending.setdefault(stamp, Sample(stamp, time.monotonic_ns(), 0, stamp,
                                                     msg.header.frame_id, (p.x, p.y, p.z)))
        while len(self.com_pending) > 10:
            del self.com_pending[min(self.com_pending)]

    def _motion(self, key, msg):
        value = dict(state=msg.state, phase=msg.phase, swing_foot=msg.swing_foot,
                     generation=msg.generation, model_sha256=msg.model_sha256,
                     ready=msg.ready, stopped=msg.stopped, fault_reason=msg.fault_reason,
                     stamp_ns=msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec,
                     received_ns=time.monotonic_ns())
        self.motion[key] = value
        self._write(key+'_state', value)

    def _tf(self, msg, info):
        try:
            raw_gid = info.get('publisher_gid') if isinstance(info, dict) else getattr(info, 'publisher_gid', None)
            if (raw_gid is None and isinstance(info, dict)
                    and type(info.get('source_timestamp')) is int
                    and type(info.get('received_timestamp')) is int):
                self.tf_api = dict(publisher_gid_available=False,
                                  authority_source='required_native_cpp_observer')
                return  # this API capability is not a native runtime fault
            gid_bytes = bytes(raw_gid) if raw_gid is not None else b''
            if not gid_bytes:
                raise ValueError('missing publisher_gid')
            gid = gid_bytes.hex()
        except (ValueError, TypeError) as error:
            self.errors.append('tf_metadata:'+str(error))
            return  # retain a usable executor for explicit owner/engine cleanup
        for transform in msg.transforms:
            self.transforms.append(dict(parent=transform.header.frame_id,
                child=transform.child_frame_id, gid=gid,
                stamp_ns=transform.header.stamp.sec*1_000_000_000+transform.header.stamp.nanosec))

    def _frame(self):
        ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
        samples = asdict(self.inbox.bundle(ros_ns))
        eligible = [stamp for stamp in self.com_pending if stamp <= ros_ns]
        if eligible:
            latest = max(eligible)
            self.native_com = self.com_pending[latest]
            for stamp in list(self.com_pending):
                if stamp <= latest:
                    del self.com_pending[stamp]
        samples['native_com'] = asdict(self.native_com) if self.native_com else None
        absent = [key for key, value in samples.items() if value is None]
        if absent:
            self.missing.update(absent)
            return
        row = dict(ros_ns=ros_ns, wall_ns=wall_ns, stage=self.stage, samples=samples,
                   crawl=dict(self.motion.get('crawl', {})))
        self.frames.append(row)
        self._write('frame', row)

    def fault(self):
        with self._lock:
            faults = [key+':'+value['fault_reason'] for key, value in self.motion.items() if value['fault_reason']]
            return (self.errors+faults)[0] if self.errors or faults else ''

    def owner_graph(self):
        topics = ('/clock', '/joint_states', '/odom', '/navigation/odom', '/scan', '/navigation/imu',
                  '/navigation/foot_contacts', '/navigation/native_com', '/navigation/carry_state',
                  '/leg_position_controller/commands', '/gripper_position_controller/commands',
                  '/navigation/cmd_vel')
        topics += ('/navigation/native_controls',)
        return {topic: [dict(node=value.node_namespace+'/'+value.node_name,
                            gid=bytes(value.endpoint_gid).hex())
                        for value in self.get_publishers_info_by_topic(topic)] for topic in topics}

    def close_log(self):
        self.raw.flush()
        self.raw.close()
