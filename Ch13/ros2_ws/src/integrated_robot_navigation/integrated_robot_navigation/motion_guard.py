"""Short safety kernel. ROS activation must also verify the native profile.

The kernel is not a native-validation authority. Only its ROS service wrapper
may expose activation, after loading/verifying a bound CarryProfile.
"""
import math
import json
from pathlib import Path
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState, Imu, LaserScan
from integrated_robot_interfaces.msg import FootContacts, MotionState
from integrated_robot_interfaces.srv import SetMode

from .carry_profile import CarryProfile, _validate_limits, validate_profile
from .model import compile_model
from .projection import body_data, body_rotation
from .samples import SensorBundle, Sample, Vec3, sample_valid, validate_bundle

OWNERS = ('raw', 'smoothed', 'final', 'legs', 'joints', 'imu', 'contacts', 'body', 'scan', 'carry')
ZERO = (0., 0., 0.)


class MotionGuard:
    def __init__(self, model, limits, carry_q):
        _validate_limits(limits)
        if len(carry_q) != 6 or not all(math.isfinite(v) for v in carry_q):
            raise ValueError('six carry angles required')
        self.model, self.limits, self.carry_q = model, dict(limits), tuple(carry_q)
        self.generation, self.engine_epoch = 0, 0
        self.mode, self.fault = 'HOLD', ''
        self.owners = {}
        self.last_ros = self.last_wall = self.progress_wall = None
        self.restart_required = False

    def observe_owners(self, counts):
        self.owners = dict(counts)

    def fail(self, reason):
        if not self.fault:
            self.fault = reason
        return ZERO, self.fault

    def set_mode(self, mode):
        if mode == 'RESET':
            if self.restart_required:
                return False, 'restart_required'
            self.generation += 1
            self.mode, self.fault = 'HOLD', ''
            self.last_ros = self.last_wall = self.progress_wall = None
            return True, ''
        if mode not in ('STAND', 'CRAWL', 'HOLD', 'STOP'):
            return False, 'unsupported_mode'
        if self.fault:
            return False, self.fault
        self.mode = mode
        return True, ''

    def evaluate(self, bundle: SensorBundle, raw: Sample, smoothed: Sample,
                 ros_ns: int, wall_ns: int) -> tuple[Vec3, str]:
        if (self.last_ros is not None and ros_ns < self.last_ros or
                self.last_wall is not None and wall_ns < self.last_wall):
            self.restart_required = True
            return self.fail('clock_rollback')
        if self.last_ros is None or ros_ns > self.last_ros:
            self.progress_wall = wall_ns
        self.last_ros, self.last_wall = ros_ns, wall_ns
        if self.fault:
            return ZERO, self.fault
        if self.mode != 'CRAWL':
            return ZERO, ''
        # Raw is independent of the smoother and is checked first.
        for name, value in (('raw', raw), ('smoothed', smoothed)):
            ok, reason = sample_valid(value, ros_ns, wall_ns, self.generation,
                                      max_age_ns=200_000_000)
            if not ok:
                return self.fail(name+':'+reason)
            if (value.frame_id != 'nav_base' or not isinstance(value.data, (tuple, list)) or len(value.data) != 3
                    or abs(value.data[0]) > self.limits['max_vx']
                    or value.data[1] != 0. or abs(value.data[2]) > self.limits['max_wz']):
                return self.fail(name+':command_limit_or_frame')
        if wall_ns-self.progress_wall > 200_000_000:
            return self.fail('clock_paused')
        for name in OWNERS:
            if self.owners.get(name) != 1:
                return self.fail('owner:'+name)
        ok, reason = validate_bundle(bundle, ros_ns, wall_ns, self.engine_epoch)
        if not ok:
            return self.fail(reason)
        try:
            carry = bundle.carry.data
            if (carry['ready'] is not True or carry['generation'] != self.generation
                    or carry['model_sha256'] != self.model.model_sha256):
                return self.fail('carry:not_ready_or_binding')
            q, qd = bundle.joints.data['position'], bundle.joints.data['velocity']
            if set(q) != set(self.model.limits) or set(qd) != set(q):
                return self.fail('joints:names')
            for name, value in q.items():
                lo, hi, velocity, _ = self.model.limits[name]
                if not lo <= value <= hi or abs(qd[name]) > velocity:
                    return self.fail('joints:physical_limit')
            for i, target in enumerate(self.carry_q, 1):
                name = f'arm_joint_{i}'
                if (abs(q[name]-target) > self.limits['carry_error_rad']
                        or abs(qd[name]) > self.limits['carry_velocity_rps']):
                    return self.fail('carry:measured_drift')
            if bundle.body.frame_id != 'odom' or bundle.body.data['child_frame_id'] != 'base_footprint':
                return self.fail('body:frame')
            _, (roll, pitch, _) = body_rotation(bundle.body.data)
            z = bundle.body.data['position'][2]
            if (max(abs(roll), abs(pitch)) > self.limits['max_roll_pitch']
                    or not self.limits['min_body_height_m'] <= z <= self.limits['max_body_height_m']):
                return self.fail('body:stability')
            contacts = bundle.contacts.data
            if (bundle.contacts.frame_id != 'odom'
                    or tuple(contacts['names']) != self.model.feet
                    or contacts['unexpected_contacts'] != 0):
                return self.fail('contacts:frame_names_or_unexpected')
            if (len(contacts['forces']) != 4 or len(contacts['touching']) != 4
                    or sum(contacts['touching']) < 3
                    or any(bool(touch) != (force >= self.limits['min_contact_force_n'])
                           for touch, force in zip(contacts['touching'], contacts['forces']))):
                return self.fail('contacts:support')
            if bundle.imu.frame_id != 'base_link' or bundle.scan.frame_id != 'lidar_link':
                return self.fail('sensor:frame')
            scan = bundle.scan.data
            if (len(scan['ranges']) != 360 or len(scan['hits']) != 360
                    or not 0. < scan['range_min'] < scan['range_max']
                    or any(not scan['range_min'] <= value <= scan['range_max'] for value in scan['ranges'])):
                return self.fail('scan:invalid')
        except (KeyError, TypeError, ValueError, IndexError):
            return self.fail('sensor:schema')
        return tuple(float(v) for v in smoothed.data), ''


class MotionGuardNode(Node):
    """Serialized ROS receiver + independent monotonic watchdog, one final owner.

    model/profile constructor injection is also used by embedded launchers; no
    parameter or service can bypass validate_profile. Headerless Twist generation
    cutoffs use DDS SYSTEM source timestamps on this same-host native benchmark.
    Sensor capture ROS times and local monotonic receipt remain separate.
    """
    TOPICS = {
        'raw': '/navigation/cmd_vel_raw', 'smoothed': '/navigation/cmd_vel_smoothed',
        'final': '/navigation/cmd_vel', 'legs': '/leg_position_controller/commands',
        'joints': '/joint_states', 'imu': '/navigation/imu', 'contacts': '/navigation/foot_contacts',
        'body': '/odom', 'scan': '/scan', 'carry': '/navigation/carry_state',
    }

    def __init__(self, model=None, profile=None, engine=None, **kwargs):
        super().__init__('motion_guard', **kwargs)
        model_file = self.declare_parameter('model_file', '').value
        profile_file = self.declare_parameter('carry_profile', '').value
        selected = self.declare_parameter('engine', 'mujoco').value
        self.model = model if model is not None else compile_model(Path(model_file).read_text())
        self.profile = profile if profile is not None else CarryProfile(**json.loads(Path(profile_file).read_text()))
        self.engine = engine or selected
        self.core = MotionGuard(self.model, self.profile.limits, self.profile.arm_q)
        self.lock = threading.RLock()
        self.samples = {key: None for key in ('joints', 'imu', 'contacts', 'body', 'scan', 'carry')}
        self.pending = {key: {} for key in self.samples}
        self.commands = {'raw': None, 'smoothed': None}
        self.command_sources = {}
        self.owner_ids = {}
        self.reset_ros = -1
        self.reset_system = time.time_ns()
        self.closing = False
        self.pub = self.create_publisher(Twist, self.TOPICS['final'], 10)
        self.state_pub = self.create_publisher(MotionState, '/navigation/guard_state', 10)
        qos = qos_profile_sensor_data
        self.create_subscription(JointState, self.TOPICS['joints'],
                                 lambda msg: self._sensor('joints', msg), qos)
        self.create_subscription(Imu, self.TOPICS['imu'], lambda msg: self._sensor('imu', msg), qos)
        self.create_subscription(FootContacts, self.TOPICS['contacts'],
                                 lambda msg: self._sensor('contacts', msg), qos)
        self.create_subscription(Odometry, self.TOPICS['body'], lambda msg: self._sensor('body', msg), qos)
        self.create_subscription(LaserScan, self.TOPICS['scan'], lambda msg: self._sensor('scan', msg), qos)
        self.create_subscription(MotionState, self.TOPICS['carry'], lambda msg: self._sensor('carry', msg), qos)
        self.create_subscription(Twist, self.TOPICS['raw'], self._raw, 10)
        self.create_subscription(Twist, self.TOPICS['smoothed'], self._smoothed, 10)
        self.create_service(SetMode, '/navigation/set_mode', self._mode)
        self.create_timer(.05, self._owners, clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.stopping = threading.Event()
        self.worker = threading.Thread(target=self._watchdog, name='navigation_motion_watchdog')
        self.worker.start()  # last: constructor failure cannot orphan a started worker

    def _owners(self):
        endpoints = {name: tuple(sorted(bytes(value.endpoint_gid) for value in
                       self.get_publishers_info_by_topic(topic))) for name, topic in self.TOPICS.items()}
        counts = {name: len(values) for name, values in endpoints.items()}
        with self.lock:
            if self.core.mode == 'CRAWL' and self.owner_ids:
                for name, current in endpoints.items():
                    if current != self.owner_ids.get(name):
                        self.core.fail('owner_identity:'+name)
                        break
            else:
                self.owner_ids = endpoints
            self.core.observe_owners(counts)

    def _raw(self, msg, info):
        self._command('raw', msg, info)

    def _smoothed(self, msg, info):
        self._command('smoothed', msg, info)

    def _command(self, key, msg, info):
        source = info.get('source_timestamp', 0) if isinstance(info, dict) else getattr(info, 'source_timestamp', 0)
        with self.lock:
            if self.closing or source < self.reset_system or source <= self.command_sources.get(key, -1):
                return
            if source <= 0:
                if self.core.mode == 'CRAWL':
                    self.core.fail('command:missing_dds_source_time')
                return
            self.command_sources[key] = source
            value = (msg.linear.x, msg.linear.y, msg.angular.z)
            if any(v != 0. for v in (msg.linear.z, msg.angular.x, msg.angular.y)):
                self.core.fail('command:nonplanar')
                return
            self.commands[key] = Sample(self.get_clock().now().nanoseconds, time.monotonic_ns(),
                self.core.generation, source, 'nav_base', value)

    def _sensor(self, key, msg):
        receipt = time.monotonic_ns()
        stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        try:
            frame = msg.header.frame_id
            if key == 'joints':
                if len(set(msg.name)) != len(msg.name) or len(msg.position) != len(msg.name) or len(msg.velocity) != len(msg.name):
                    raise ValueError('joint shape/names')
                data = dict(position=dict(zip(msg.name, msg.position)), velocity=dict(zip(msg.name, msg.velocity)))
                frame = 'base_link'  # joint axes are identified by model names, not a Cartesian header
            elif key == 'imu':
                a, w = msg.linear_acceleration, msg.angular_velocity
                data = dict(acceleration=(a.x, a.y, a.z), angular_velocity=(w.x, w.y, w.z))
            elif key == 'contacts':
                if msg.epoch != self.core.engine_epoch:
                    raise ValueError('engine epoch changed; restart required')
                data = dict(names=tuple(msg.names), points=tuple((p.x, p.y, p.z) for p in msg.points),
                    forces=tuple(msg.normal_forces), touching=tuple(msg.touching), unexpected_contacts=msg.unexpected_contacts)
            elif key == 'body':
                data = body_data(msg)
            elif key == 'scan':
                if any(math.isnan(v) or v < msg.range_min or v == -math.inf for v in msg.ranges):
                    raise ValueError('invalid native scan range')
                data = dict(ranges=tuple(min(v, msg.range_max) for v in msg.ranges),
                    hits=tuple(math.isfinite(v) and v <= msg.range_max for v in msg.ranges),
                    range_min=msg.range_min, range_max=msg.range_max,
                    angle_min=msg.angle_min, angle_increment=msg.angle_increment)
            else:
                data = dict(ready=msg.ready, generation=msg.generation, model_sha256=msg.model_sha256)
            sample = Sample(stamp, receipt, self.core.engine_epoch, stamp, frame, data)
            with self.lock:
                previous = self.samples[key]
                if (self.closing or stamp <= self.reset_ros or
                        previous is not None and stamp <= previous.stamp_ns):
                    return
                self.pending[key].setdefault(stamp, sample)
                while len(self.pending[key]) > 10:
                    del self.pending[key][min(self.pending[key])]
        except (TypeError, ValueError) as error:
            with self.lock:
                if self.core.mode == 'CRAWL':
                    self.core.fail(key+':'+str(error))

    def _bundle(self, ros_ns):
        # Clock and sensor DDS callbacks may arrive in different orders. Buffer
        # future captures; never accept them early or renew their first receipt.
        for key, candidates in self.pending.items():
            eligible = [stamp for stamp in candidates if stamp <= ros_ns]
            if eligible:
                latest = max(eligible)
                self.samples[key] = candidates[latest]
                for stamp in list(candidates):
                    if stamp <= latest:
                        del candidates[stamp]
        return SensorBundle(**self.samples)

    def _mode(self, request, response):
        with self.lock:
            generation = self.core.generation
        if request.mode == 'CRAWL':
            accepted, reason = validate_profile(self.profile, self.model, self.engine)
            if not accepted:
                response.accepted, response.message = False, reason
                return response
        with self.lock:
            if self.closing or generation != self.core.generation:
                response.accepted, response.message = False, 'owner_generation_changed'
                return response
            response.accepted, response.message = self.core.set_mode(request.mode)
            if response.accepted and request.mode == 'RESET':
                self.reset_ros = self.get_clock().now().nanoseconds
                self.reset_system = time.time_ns()
                self.samples = {key: None for key in self.samples}
                self.pending = {key: {} for key in self.samples}
                self.commands = {'raw': None, 'smoothed': None}
                self.command_sources.clear()
                self.owner_ids.clear()
        return response

    def _publish(self, value, reason):
        msg = Twist()
        msg.linear.x, msg.linear.y, msg.angular.z = value
        self.pub.publish(msg)
        status = MotionState()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = 'nav_base'
        status.generation = self.core.generation
        status.model_sha256 = self.model.model_sha256
        status.state = 'FAULT' if reason else self.core.mode
        status.ready = not reason and self.core.mode == 'CRAWL'
        status.fault_reason = reason
        status.stopped = False  # only crawl's measured landing/velocity gate can assert this
        self.state_pub.publish(status)

    def _watchdog(self):
        while not self.stopping.wait(.02):
            try:
                with self.lock:
                    ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
                    value, reason = self.core.evaluate(self._bundle(ros_ns), self.commands['raw'],
                                                      self.commands['smoothed'], ros_ns, wall_ns)
                    self._publish(value, reason)
            except Exception as error:
                with self.lock:
                    self.core.fail('watchdog_exception:'+type(error).__name__)
        with self.lock:
            self._publish(ZERO, self.core.fault)

    def destroy_node(self):
        with self.lock:
            self.closing = True
            if not self.core.fault:
                self.core.set_mode('STOP')
        self.stopping.set()
        self.worker.join(timeout=2.)
        if self.worker.is_alive():
            raise RuntimeError('motion watchdog did not join; ROS resources retained')
        return super().destroy_node()


def main(args=None):
    from integrated_robot_vision.execution import run_node
    run_node(MotionGuardNode, args=args)
