"""Lifecycle-managed sole leg owner; bootstrap STAND is not permission to crawl."""
from copy import deepcopy
import json
import math
from pathlib import Path
import threading
import time

from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState, Imu, LaserScan
from std_msgs.msg import Float64MultiArray
from integrated_robot_interfaces.msg import FootContacts, MotionState

from .carry_profile import CarryProfile, validate_profile
from .gait import CrawlMachine
from .model import compile_model
from .observations import SensorInbox, sensor_sample
from .samples import Sample, sample_valid


class CrawlController(LifecycleNode):
    def __init__(self, model=None, profile=None, engine=None, **kwargs):
        super().__init__('crawl_controller', **kwargs)
        self.model_file = self.declare_parameter('model_file', '').value
        self.profile_file = self.declare_parameter('carry_profile', '').value
        self.engine = engine or self.declare_parameter('engine', 'mujoco').value
        self.model, self.profile = model, profile
        self.lock = threading.RLock()
        self.inbox = SensorInbox(0)
        self.machine = None
        self.active = self.closing = False
        self.generation = 0
        self.gate, self.gate_receipt, self.command = None, 0, None
        self.cutoff_system = time.time_ns()
        self.last_command_source = -1
        self.stop_reason = ''
        self.admission = (False, 'not_configured')
        self._stand_since = None
        self._gate_owner = None
        self.legs = self.create_lifecycle_publisher(Float64MultiArray,
            '/leg_position_controller/commands', 10)
        self.status = self.create_publisher(MotionState, '/navigation/crawl_state', 10)
        for key, kind, topic in (
            ('joints', JointState, '/joint_states'), ('imu', Imu, '/navigation/imu'),
            ('contacts', FootContacts, '/navigation/foot_contacts'), ('body', Odometry, '/odom'),
            ('scan', LaserScan, '/scan'), ('carry', MotionState, '/navigation/carry_state')):
            def receive(msg, stream=key):
                self._sensor(stream, msg)
            self.create_subscription(kind, topic, receive, qos_profile_sensor_data)
        self.create_subscription(MotionState, '/navigation/guard_state', self._gate, 10)
        self.create_subscription(Twist, '/navigation/cmd_vel', self._command, 10)
        self.create_timer(.02, self._tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def _sensor(self, key, msg):
        try:
            sample = sensor_sample(key, msg, time.monotonic_ns(), self.inbox.epoch)
            with self.lock:
                if not self.closing:
                    self.inbox.receive(key, sample)
        except (ValueError, TypeError) as error:
            with self.lock:
                if self.active and self.machine:
                    self.machine._fail(key+':'+str(error))

    def _gate(self, msg):
        with self.lock:
            if not self.closing:
                self.gate, self.gate_receipt = deepcopy(msg), time.monotonic_ns()

    def _command(self, msg, info):
        source = info.get('source_timestamp', 0) if isinstance(info, dict) else getattr(info, 'source_timestamp', 0)
        with self.lock:
            if self.closing or source < self.cutoff_system or source <= self.last_command_source:
                return
            self.last_command_source = source
            if any(v != 0. for v in (msg.linear.y, msg.linear.z, msg.angular.x, msg.angular.y)):
                if self.active and self.machine:
                    self.machine._fail('nonplanar final command')
                return
            generation = self.gate.generation if self.gate is not None else -1
            self.command = Sample(self.get_clock().now().nanoseconds, time.monotonic_ns(),
                generation, source, 'nav_base', (msg.linear.x, 0., msg.angular.z))

    def on_configure(self, state):
        try:
            if self.model is None:
                self.model = compile_model(Path(self.model_file).read_text())
            if self.profile is None:
                self.profile = CarryProfile(**json.loads(Path(self.profile_file).read_text()))
            if self.profile.model_sha256 != self.model.model_sha256:
                raise ValueError('profile model hash mismatch')
            self.machine = CrawlMachine(self.model, self.profile.limits)
            self.admission = validate_profile(self.profile, self.model, self.engine)
            self.stop_reason = ''
            return super().on_configure(state)
        except (OSError, TypeError, KeyError, ValueError) as error:
            self.get_logger().error('crawl configure rejected: '+str(error))
            return TransitionCallbackReturn.FAILURE

    def _gate_valid(self, ros_ns, wall_ns):
        if self.gate is None:
            return False, 'missing_guard'
        sample = Sample(self.gate.header.stamp.sec*1_000_000_000+self.gate.header.stamp.nanosec,
            self.gate_receipt, self.generation, 0, self.gate.header.frame_id,
            (self.gate.generation, self.gate.model_sha256, self.gate.state, self.gate.ready))
        ok, reason = sample_valid(sample, ros_ns, wall_ns, self.generation, max_age_ns=200_000_000)
        if not ok:
            return False, 'guard:'+reason
        if self.gate.model_sha256 != self.model.model_sha256 or self.gate.generation != self.generation:
            return False, 'guard_generation_or_model'
        ids = tuple(sorted(bytes(row.endpoint_gid) for row in self.get_publishers_info_by_topic('/navigation/guard_state')))
        if len(ids) != 1 or self._gate_owner is not None and ids != self._gate_owner:
            return False, 'guard_owner'
        return True, ''

    def on_activate(self, state):
        with self.lock:
            if self.machine is None or self.gate is None:
                return TransitionCallbackReturn.FAILURE
            ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
            self.generation = self.gate.generation
            self._gate_owner = None
            valid, reason = self._gate_valid(ros_ns, wall_ns)
            if not valid or self.gate.state not in ('STAND', 'HOLD'):
                self.get_logger().warning('activate requires fresh STAND/HOLD guard: '+reason)
                return TransitionCallbackReturn.FAILURE
            self.machine.reset(self.inbox.bundle(ros_ns), ros_ns, wall_ns)
            if self.machine.state == 'FAULT':
                self.get_logger().warning('activate missing/invalid feedback: '+self.machine.reason)
                return TransitionCallbackReturn.FAILURE
            self.machine.generation = self.generation
            self._gate_owner = tuple(sorted(bytes(row.endpoint_gid) for row in
                self.get_publishers_info_by_topic('/navigation/guard_state')))
            self.stop_reason, self.command, self._stand_since = '', None, None
            self.cutoff_system, self.last_command_source = time.time_ns(), -1
            result = super().on_activate(state)
            self.active = result == TransitionCallbackReturn.SUCCESS
            return result

    def on_deactivate(self, state):
        with self.lock:
            if self.machine and self.machine.state not in ('STAND', 'STOPPED', 'FAULT', 'INACTIVE'):
                self.machine.request_stop(urgent=False)
                self.stop_reason = self.stop_reason or 'deactivation_requires_measured_stop'
                return TransitionCallbackReturn.FAILURE
            self.active = False
            return super().on_deactivate(state)

    def on_cleanup(self, state):
        with self.lock:
            self.active = False
            self.machine = None
            self.command, self.gate = None, None
            self.inbox.clear(self.get_clock().now().nanoseconds)
            return super().on_cleanup(state)

    def on_shutdown(self, state):
        with self.lock:
            self.active = False
            return super().on_shutdown(state)

    def _stand_ready(self, bundle, result, now):
        if result.state != 'STAND' or result.joint_targets is None:
            self._stand_since = None
            return False
        limits = self.machine.limits
        q, qd = bundle.joints.data['position'], bundle.joints.data['velocity']
        body = bundle.body.data
        healthy = (all(bundle.contacts.data['touching'])
            and all(abs(q[n]-target) <= .03 and abs(qd[n]) <= .02 for n, target in result.joint_targets.items())
            and math.hypot(*body['linear_velocity'][:2]) <= limits['stopped_v_mps']
            and abs(body['angular_velocity'][2]) <= limits['stopped_wz_rps'])
        if not healthy:
            self._stand_since = None
            return False
        if self._stand_since is None:
            self._stand_since = now
        return now-self._stand_since >= int(limits['settle_s']*1e9)

    def _publish_status(self, result=None, stand_ready=False):
        if result is None and self.machine is not None:
            # Inactive means no commands, not that a latched fault disappeared.
            result = self.machine._result()
        status = MotionState()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = 'base_link'
        status.generation = self.generation
        status.model_sha256 = self.model.model_sha256 if self.model else ''
        status.state = result.state if result is not None and self.active else 'INACTIVE'
        if result is not None:
            status.phase, status.swing_foot = result.phase, result.swing_foot or ''
            status.fault_reason = result.reason or self.stop_reason
        status.ready = self.active and not status.fault_reason and (stand_ready or status.state == 'CRAWL')
        status.stopped = self.active and (stand_ready or status.state == 'STOPPED')
        self.status.publish(status)

    def _tick(self):
        with self.lock:
            if self.closing:
                return
            if not self.active or self.machine is None:
                self._publish_status()
                return
            ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
            bundle = self.inbox.bundle(ros_ns)
            if self.count_publishers('/leg_position_controller/commands') != 1:
                self.machine._fail('owner:legs')
            valid, reason = self._gate_valid(ros_ns, wall_ns)
            if not valid or self.gate.fault_reason or self.gate.state == 'FAULT':
                self.stop_reason = self.stop_reason or reason or self.gate.fault_reason or 'guard_fault'
                self.machine.request_stop(urgent=True)
            command = (0., 0., 0.)
            if valid and self.gate.state == 'CRAWL' and self.gate.ready and not self.stop_reason:
                if not self.admission[0]:
                    self.machine._fail(self.admission[1])
                else:
                    fresh, why = sample_valid(self.command, ros_ns, wall_ns, self.generation, max_age_ns=200_000_000)
                    if not fresh:
                        self.stop_reason = 'final_command:'+why
                        self.machine.request_stop(urgent=True)
                    else:
                        command = self.command.data
            elif self.machine.state == 'CRAWL':
                self.machine.request_stop(urgent=self.gate is None or bool(self.gate.fault_reason))
            result = self.machine.advance(bundle, command, ros_ns, wall_ns)
            ready = False
            if result.joint_targets is not None:
                self.legs.publish(Float64MultiArray(data=[result.joint_targets[n] for n in self.model.joint_names]))
                ready = self._stand_ready(bundle, result, wall_ns)
            self._publish_status(result, ready)

    def destroy_node(self):
        with self.lock:
            self.closing, self.active = True, False
        return super().destroy_node()


def main(args=None):
    from integrated_robot_vision.execution import run_node
    run_node(CrawlController, args=args)
