"""Lifecycle-managed sole leg owner; bootstrap STAND is not permission to crawl."""
from copy import deepcopy
from collections import deque
from dataclasses import asdict
import json
import math
from pathlib import Path
import threading
import time

from rclpy.lifecycle import TransitionCallbackReturn
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState, Imu, LaserScan
from std_msgs.msg import Float64MultiArray
from std_srvs.srv import Trigger
from integrated_robot_interfaces.msg import FootContacts, MotionState

from .carry_profile import CarryProfile, validate_profile
from .gait import CrawlMachine
from .model import compile_model, initial_leg_targets
from .observations import SensorInbox, sensor_sample
from .samples import Sample, sample_valid
from .clock_execution import ControlClockLifecycleNode


class CrawlController(ControlClockLifecycleNode):
    def __init__(self, model=None, profile=None, engine=None, **kwargs):
        super().__init__('crawl_controller', **kwargs)
        self.model_file = self.declare_parameter('model_file', '').value
        self.profile_file = self.declare_parameter('carry_profile', '').value
        self.validation_mode = self.declare_parameter('validation_mode', False).value
        self.clock_mode = self.declare_parameter('control_clock_mode', 'native').value
        if self.clock_mode not in ('native','relay100') or (self.clock_mode == 'relay100' and not self.validation_mode):
            super().destroy_node()
            raise ValueError('control_clock_mode experiment requires validation_mode')
        self.engine = engine or self.declare_parameter('engine', 'mujoco').value
        self.model, self.profile = model, profile
        self.lock = threading.RLock()
        # Lock order: model owner -> mailbox. Receivers never acquire the
        # model lock or mutate CrawlMachine, including malformed input paths.
        self.inbox_lock = threading.RLock()
        self._ingress_fault = None
        self.sensor_group = MutuallyExclusiveCallbackGroup() if self.clock_mode == 'relay100' else None
        self.inbox = SensorInbox(0)
        self.machine = None
        self.active = self.closing = False
        self.generation = 0
        self.gate, self.gate_receipt, self.command = None, 0, None
        self._gate_pending = {}
        self.cutoff_system = time.time_ns()
        self.last_command_source = -1
        self.stop_reason = ''
        self.admission = (False, 'not_configured')
        self._stand_since = None
        self._last_stand_ready = False
        self.first_fault = None
        self.first_stop = None
        self.guard_receipts, self.tick_spans = deque(maxlen=16), deque(maxlen=16)
        self.contact_ingress = deque(maxlen=16)
        self.clock_read_span = None
        self.tick_dispatch_started_ns = None
        self._gate_owner = None
        self._held_targets, self._held_model_sha = None, None
        self.legs = self.create_lifecycle_publisher(Float64MultiArray,
            '/leg_position_controller/commands', 10)
        self.status = self.create_publisher(MotionState, '/navigation/crawl_state', 10)
        for key, kind, topic in (
            ('joints', JointState, '/joint_states'), ('imu', Imu, '/navigation/imu'),
            ('contacts', FootContacts, '/navigation/foot_contacts'), ('body', Odometry, '/odom'),
            ('scan', LaserScan, '/scan'), ('carry', MotionState, '/navigation/carry_state')):
            def receive(msg, stream=key):
                self._sensor(stream, msg)
            self.create_subscription(kind, topic, receive, qos_profile_sensor_data,
                                     callback_group=self.sensor_group)
        self.create_subscription(MotionState, '/navigation/guard_state', self._gate, 10,
                                 callback_group=self.sensor_group)
        self.create_subscription(Twist, '/navigation/cmd_vel', self._command, 10)
        self.create_service(Trigger, '~/calibrate_contact', self._calibrate_contact)
        self.create_service(Trigger, '~/report', self._report)
        self.create_timer(.02, self._dispatch_tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def _sensor(self, key, msg):
        receipt = time.monotonic_ns()
        with self.inbox_lock:
            if self.closing:
                return
            try:
                sample = sensor_sample(key, msg, receipt, self.inbox.epoch)
                if not self.closing:
                    self.inbox.receive(key, sample)
                    if key == 'contacts':
                        self.contact_ingress.append(dict(stamp_ns=sample.stamp_ns,
                            received_wall_ns=sample.received_ns, cache_admitted_wall_ns=time.monotonic_ns()))
            except (ValueError, TypeError) as error:
                if self.active and self._ingress_fault is None:
                    self._ingress_fault = key+':'+str(error)

    def _bundle_snapshot(self, ros_ns, wall_ns=None):
        with self.inbox_lock:
            return self.inbox.bundle(ros_ns,wall_ns=wall_ns)

    def _gate(self, msg):
        entry_wall_ns = time.monotonic_ns()
        with self.inbox_lock:
            if not self.closing:
                stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
                receipt = entry_wall_ns
                previous = -1 if self.gate is None else (
                    self.gate.header.stamp.sec*1_000_000_000+self.gate.header.stamp.nanosec)
                if stamp > previous:
                    self._gate_pending.setdefault(stamp, (deepcopy(msg), receipt))
                    while len(self._gate_pending) > 10:
                        del self._gate_pending[min(self._gate_pending)]
                self.guard_receipts.append(dict(
                    stamp_ns=stamp, entry_wall_ns=entry_wall_ns, received_ns=receipt,
                    received_ros_ns=self.get_clock().now().nanoseconds))

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
            if self._held_targets is None:
                self._held_targets = initial_leg_targets(self.model)
                self._held_model_sha = self.model.model_sha256
            elif self._held_model_sha != self.model.model_sha256:
                raise ValueError('held command model changed; cold restart required')
            self.machine = CrawlMachine(self.model, self.profile.limits)
            self.admission = validate_profile(self.profile, self.model, self.engine)
            self.stop_reason = ''
            return super().on_configure(state)
        except (OSError, TypeError, KeyError, ValueError) as error:
            self.get_logger().error('crawl configure rejected: '+str(error))
            return TransitionCallbackReturn.FAILURE

    def _select_gate(self, ros_ns, *, wall_ns=None):
        # Independent /clock and status subscriptions need not dispatch in
        # capture order. Hold a future candidate, never retag or use it early.
        with self.inbox_lock:
            eligible = [stamp for stamp,(_,receipt) in self._gate_pending.items()
                        if stamp <= ros_ns and (wall_ns is None or receipt <= wall_ns)]
            if eligible:
                latest = max(eligible)
                self.gate, self.gate_receipt = self._gate_pending[latest]
                for stamp in list(self._gate_pending):
                    if stamp <= latest:
                        del self._gate_pending[stamp]

    def _gate_valid(self, ros_ns, wall_ns):
        self._select_gate(ros_ns,wall_ns=wall_ns)
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

    def _calibration_carry(self, ros_ns, wall_ns, *, bundle=None):
        # A control tick must validate the SAME selected carry sample as its
        # other measurements and first-stop report. Never reselect mid-tick.
        sample = (self._bundle_snapshot(ros_ns,wall_ns) if bundle is None else bundle).carry
        ok, reason = sample_valid(sample, ros_ns, wall_ns, self.inbox.epoch, max_age_ns=200_000_000)
        if not ok:
            return False, 'calibration_carry:'+reason
        value = sample.data
        return (value['ready'] and value['generation'] == self.generation
                and value['model_sha256'] == self.model.model_sha256
                and self.count_publishers('/navigation/carry_state') == 1), 'calibration_carry_not_ready'

    def _calibrate_contact(self, request, response):
        with self.lock:
            if (self.closing or not self.active or not self.validation_mode or self.machine is None
                    or self.machine.state != 'STAND' or not self._last_stand_ready or self.stop_reason):
                response.message = 'requires validation mode and measured idle STAND'
                return response
            ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
            valid, reason = self._gate_valid(ros_ns, wall_ns)
            carry, carry_reason = self._calibration_carry(ros_ns, wall_ns)
            if not valid or self.gate.state != 'STAND' or not carry:
                response.message = reason or carry_reason or 'STAND gate required'
                return response
            try:
                self.machine.request_contact_calibration(ros_ns=ros_ns,wall_ns=wall_ns)
                self._last_stand_ready = False
                response.success = True
                response.message = 'one in-place FL contact calibration reserved; no CRAWL permission'
            except ValueError as error:
                response.message = str(error)
            return response

    def on_activate(self, state):
        with self.lock:
            with self.inbox_lock:
                if self._ingress_fault is not None:
                    return TransitionCallbackReturn.FAILURE
            ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
            self._select_gate(ros_ns,wall_ns=wall_ns)
            if self.machine is None or self.gate is None:
                return TransitionCallbackReturn.FAILURE
            self.generation = self.gate.generation
            self._gate_owner = None
            valid, reason = self._gate_valid(ros_ns, wall_ns)
            if not valid or self.gate.state not in ('STAND', 'HOLD'):
                self.get_logger().warning('activate requires fresh STAND/HOLD guard: '+reason)
                return TransitionCallbackReturn.FAILURE
            if self.count_publishers('/leg_position_controller/commands') != 1:
                self.get_logger().warning('activate requires sole leg command owner')
                return TransitionCallbackReturn.FAILURE
            self.machine.reset(self._bundle_snapshot(ros_ns,wall_ns), ros_ns, wall_ns,
                               held_targets=self._held_targets)
            if self.machine.state == 'FAULT':
                self.get_logger().warning('activate missing/invalid feedback: '+self.machine.reason)
                return TransitionCallbackReturn.FAILURE
            self.machine.generation = self.generation
            self._gate_owner = tuple(sorted(bytes(row.endpoint_gid) for row in
                self.get_publishers_info_by_topic('/navigation/guard_state')))
            self.stop_reason, self.command, self._stand_since = '', None, None
            self._last_stand_ready = False
            self.cutoff_system, self.last_command_source = time.time_ns(), -1
            result = super().on_activate(state)
            with self.inbox_lock:
                self.active = result == TransitionCallbackReturn.SUCCESS
            return result

    def on_deactivate(self, state):
        with self.lock:
            if self.machine and self.machine.state not in ('STAND', 'STOPPED', 'FAULT', 'INACTIVE'):
                self.machine.request_stop(urgent=False)
                self.stop_reason = self.stop_reason or 'deactivation_requires_measured_stop'
                return TransitionCallbackReturn.FAILURE
            with self.inbox_lock:
                self.active = False
            return super().on_deactivate(state)

    def on_cleanup(self, state):
        with self.lock:
            with self.inbox_lock:
                self.active = False
                self._ingress_fault = None
                self.inbox.clear(self.get_clock().now().nanoseconds)
                self.gate = None
                self._gate_pending.clear()
            self.machine = None
            self.command = None
            return super().on_cleanup(state)

    def on_shutdown(self, state):
        with self.lock:
            with self.inbox_lock:
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
        settled = now-self._stand_since >= int(limits['settle_s']*1e9)
        if settled and self.machine.calibrating:
            self.machine.confirm_contact_calibration(wall_ns=now)
        return settled

    def _report(self, request, response):
        with self.lock:
            with self.inbox_lock:
                selected = {key: asdict(self.inbox.samples[key]) if self.inbox.samples[key] else None
                            for key in ('body', 'contacts')}
            machine = self.machine
            current = None if machine is None else dict(
                scope='selected_cache_at_report_not_new_sensor_capture',
                ros_ns=self.get_clock().now().nanoseconds, wall_ns=time.monotonic_ns(),
                state=machine.state, phase=machine.phase, swing_foot=machine.swing_foot,
                phase_start_ns=getattr(machine, '_phase_start', None),
                plan_pending=machine._shift_plan is not None,
                shift_duration_s=getattr(machine, '_shift_duration', None),
                unload_start_ns=getattr(machine, '_unload_start', None),
                unload_origin_z=getattr(machine, '_unload_origin_z', None),
                calibration=machine.calibration_snapshot(),
                reference_body=machine.reference_body.tolist(),
                targets={key: value.tolist() for key, value in getattr(machine, '_targets', {}).items()},
                floor=dict(getattr(machine, 'floor', {})),
                last_published_leg_targets=dict(self._held_targets or {}),
                selected_body=selected['body'], selected_contacts=selected['contacts'])
            response.success = True
            response.message = json.dumps(dict(model_sha256=self.model.model_sha256 if self.model else '',
                generation=self.generation, active=self.active, first_fault=self.first_fault,
                first_stop=self.first_stop, current=current), allow_nan=False)
            return response

    def _publish_status(self, result=None, stand_ready=False, bootstrap_phase=''):
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
        if not self.active and bootstrap_phase:
            status.phase = bootstrap_phase
        status.ready = self.active and not status.fault_reason and (stand_ready or status.state == 'CRAWL')
        status.stopped = self.active and (stand_ready or status.state == 'STOPPED')
        self.status.publish(status)

    def _dispatch_tick(self):
        started = time.monotonic_ns()
        self.tick_dispatch_started_ns = started
        try:
            self._tick()
        finally:
            self.tick_spans.append(dict(started_ns=started, finished_ns=time.monotonic_ns(),
                                        ros_ns=self.get_clock().now().nanoseconds))

    def _tick(self):
        with self.lock:
            if self.closing:
                return
            if not self.active or self.machine is None:
                phase = 'BOOTSTRAP_WAIT_FEEDBACK'
                if self.machine is not None and self.machine.state != 'FAULT':
                    ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
                    try:
                        _, _, _, loads, points, com = self.machine._measure(
                            self._bundle_snapshot(ros_ns,wall_ns), ros_ns, wall_ns)
                        valid, _ = self._gate_valid(ros_ns, wall_ns)
                        if (valid and self.gate.state in ('STAND', 'HOLD')
                                and self.machine._margin(com, loads, points) >= self.machine.limits['min_support_margin_m']):
                            phase = 'BOOTSTRAP_FEEDBACK_READY'
                    except (ValueError, KeyError, TypeError, IndexError):
                        pass  # absence before activation is waiting, not a motor command or recovery
                self._publish_status(bootstrap_phase=phase if not self.machine or self.machine.state != 'FAULT' else '')
                return
            clock_read_started = time.monotonic_ns()
            ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
            self.clock_read_span = dict(started_wall_ns=clock_read_started,
                finished_wall_ns=wall_ns, ros_ns=ros_ns,
                dispatch_started_wall_ns=self.tick_dispatch_started_ns)
            bundle = self._bundle_snapshot(ros_ns,wall_ns)
            with self.inbox_lock:
                if self._ingress_fault is not None:
                    self.machine._fail(self._ingress_fault)
            if self.count_publishers('/leg_position_controller/commands') != 1:
                self.machine._fail('owner:legs')
            valid, reason = self._gate_valid(ros_ns, wall_ns)
            if not valid or self.gate.fault_reason or self.gate.state == 'FAULT':
                self.stop_reason = self.stop_reason or reason or self.gate.fault_reason or 'guard_fault'
                self.machine.request_stop(urgent=True)
            if self.machine.calibrating:
                carry, why = self._calibration_carry(ros_ns, wall_ns,bundle=bundle)
                if not carry or not valid or self.gate.state != 'STAND':
                    self.stop_reason = self.stop_reason or why or 'calibration_STAND_gate_lost'
                    self.machine.request_stop(urgent=True)
            command = (0., 0., 0.)
            if valid and self.gate.state == 'CRAWL' and self.gate.ready and not self.stop_reason:
                if self.validation_mode:
                    self.machine._fail('validation_mode_forbids_crawl')
                elif not self.admission[0]:
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
            if self.stop_reason and self.first_stop is None:
                with self.inbox_lock:
                    guard_receipts = list(self.guard_receipts)
                guard = None if self.gate is None else dict(
                    stamp_ns=self.gate.header.stamp.sec*1_000_000_000+self.gate.header.stamp.nanosec,
                    received_ns=self.gate_receipt, state=self.gate.state,
                    generation=self.gate.generation, model_sha256=self.gate.model_sha256,
                    ready=self.gate.ready, fault_reason=self.gate.fault_reason)
                self.first_stop = dict(scope='first_tick_observing_stop_reason', reason=self.stop_reason,
                    ros_ns=ros_ns, wall_ns=wall_ns, guard=guard, samples=asdict(bundle),
                    guard_receipts=guard_receipts, tick_spans=list(self.tick_spans),
                    held_targets=dict(self._held_targets), state=self.machine.state)
            before = dict(state=self.machine.state, phase=self.machine.phase,
                          swing_foot=self.machine.swing_foot)
            result = self.machine.advance(bundle, command, ros_ns, wall_ns)
            ready = False
            with self.inbox_lock:
                # Fault observation, first snapshot and final publication share
                # one mailbox boundary; the model still has only this owner.
                if self._ingress_fault is not None:
                    result = self.machine._fail(self._ingress_fault)
                if result.state == 'FAULT' and self.first_fault is None:
                    ingress_snapshot = dict(wall_ns=time.monotonic_ns(),
                        contact_ingress=list(self.contact_ingress),
                        pending_capture_receipts={key: [dict(stamp_ns=sample.stamp_ns,
                            received_ns=sample.received_ns) for _, sample in sorted(pending.items())]
                            for key, pending in self.inbox.pending.items()})
                    self.first_fault = dict(scope='first_tick_observing_fault', reason=result.reason,
                        ros_ns=ros_ns, wall_ns=wall_ns, generation=self.generation,
                        model_sha256=self.model.model_sha256, samples=asdict(bundle),
                        clock_read_span=dict(self.clock_read_span),
                        contact_ingress=ingress_snapshot['contact_ingress'],
                        ingress_snapshot_wall_ns=ingress_snapshot['wall_ns'],
                        pending_capture_receipts=ingress_snapshot['pending_capture_receipts'],
                        tick_spans=list(self.tick_spans),
                        calibration=self.machine.calibration_snapshot(),
                        state_before=before, transition_during_advance=before['state'] != 'FAULT',
                        reference_body=self.machine.reference_body.tolist(),
                        targets={name: value.tolist() for name, value in self.machine._targets.items()},
                        phase_context={name: getattr(self.machine, name, None) for name in
                            ('_phase_start', '_shift_duration', '_shift_settled_start', '_unload_start')})
                if result.joint_targets is not None:
                    self.legs.publish(Float64MultiArray(data=[result.joint_targets[n] for n in self.model.joint_names]))
                    # Preserve this owner's spring preload across inactivity.
                    self._held_targets = dict(result.joint_targets)
                    ready = self._stand_ready(bundle, result, wall_ns)
            self._last_stand_ready = ready
            self._publish_status(result, ready)

    def destroy_node(self):
        with self.lock:
            with self.inbox_lock:
                self.closing, self.active = True, False
        return super().destroy_node()


def main(args=None):
    from .clock_execution import run_control_node
    run_control_node(CrawlController,args=args)
