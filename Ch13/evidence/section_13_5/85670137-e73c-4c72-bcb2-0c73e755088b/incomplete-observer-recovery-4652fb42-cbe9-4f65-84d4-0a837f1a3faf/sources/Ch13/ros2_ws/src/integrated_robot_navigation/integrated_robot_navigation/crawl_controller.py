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
from .execution_contract import read_g2_execution_scope
from .command_order import CommandOrder
from .applied_reference import AppliedReferenceCredit


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
        if self.navigation_clock_dispatch is not None and self.clock_mode != 'relay100':
            super().destroy_node()
            raise ValueError('navigation control clock requires explicit relay100 scope')
        self.engine = engine or self.declare_parameter('engine', 'mujoco').value
        self.g2_validation_mode=self.declare_parameter('g2_validation_mode',False).value
        serialized=self.declare_parameter('native_execution_profile','').value
        try:
            self.execution_profile=read_g2_execution_scope(self.validation_mode,self.g2_validation_mode,serialized,self.engine)
        except ValueError:
            super().destroy_node();raise
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
        self.command_pending = deque(maxlen=10)
        self.command_receipts = deque(maxlen=32)
        self._gate_pending = {}
        self.cutoff_system = time.time_ns()
        self.last_command_source = -1
        self.command_order = CommandOrder()
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
        self.decision_cost_trace=deque(maxlen=512)
        self._decision_cost_current=None
        self.command_publications = deque(maxlen=512)
        self.command_publication_count = 0
        self._gate_owner = None
        self._held_targets, self._held_model_sha = None, None
        self.applied_credit = None
        self._applied_pending = {}
        self._applied_owner = None
        self._credit_motion = False
        self.ingress_worker = None
        ingress_subscriptions = []
        def subscribe(*args, **kwargs):
            if self.clock_mode == 'relay100':
                # Apply the owner's existing namespace/remap rules once. The
                # ingress node must not inherit process-wide node-name remaps.
                args=(args[0],self.resolve_topic_name(args[1]),*args[2:])
                ingress_subscriptions.append((args, kwargs))
            else:
                self.create_subscription(*args, **kwargs)
        self.legs = self.create_lifecycle_publisher(Float64MultiArray,
            '/leg_position_controller/commands', 10)
        self.status = self.create_publisher(MotionState, '/navigation/crawl_state', 10)
        for key, kind, topic in (
            ('joints', JointState, '/joint_states'), ('imu', Imu, '/navigation/imu'),
            ('contacts', FootContacts, '/navigation/foot_contacts'), ('body', Odometry, '/odom'),
            ('scan', LaserScan, '/scan'), ('carry', MotionState, '/navigation/carry_state')):
            def receive(msg, stream=key):
                self._sensor(stream, msg)
            subscribe(kind, topic, receive, qos_profile_sensor_data,
                                     callback_group=self.sensor_group)
        # This is a current-state lease, not a queue of commands/events. Keep
        # reliability, but do not replay ten obsolete states after dispatch
        # resumes. Guard faults are latched; generation/binding and both age
        # limits are still checked against the original selected sample.
        subscribe(MotionState, '/navigation/guard_state',
                                 lambda msg, info: self._gate(msg, info), 1,
                                 callback_group=self.sensor_group)
        subscribe(Twist, '/navigation/cmd_vel', self._command, 10,
                                 callback_group=self.sensor_group)
        if self.engine=='mujoco' and self.g2_validation_mode:
            subscribe(JointState,'/navigation/applied_reference',
                self._applied_reference,1,callback_group=self.sensor_group)
        self.create_service(Trigger, '~/calibrate_contact', self._calibrate_contact)
        self.create_service(Trigger, '~/report', self._report)
        self.simulation_cadence=(self.engine=='mujoco' and self.g2_validation_mode
            and self.clock_mode=='relay100')
        self.last_control_dispatch_wall_ns=time.monotonic_ns()
        self.reference_dispatch=None
        self.reference_retry_hint=None
        self.reference_due_timer=None
        self.reference_due_wall_ns=None
        if self.simulation_cadence:
            from .reference_dispatch import ReferenceDispatch
            self.reference_dispatch=ReferenceDispatch()
            self.reference_retry_guard=self.create_guard_condition(self._retry_reference_tick)
            self.reference_due_timer=self.create_timer(.02,self._reference_due_tick,
                clock=Clock(clock_type=ClockType.STEADY_TIME),autostart=False)
            # One original ROSClock/TimeSource; simulation progress schedules
            # the normal 50Hz control. An independent wall watchdog below
            # remains live when that clock pauses or rolls back.
            self.create_timer(.02,self._periodic_control_tick,clock=self.get_clock())
            self.create_timer(.02,self._control_wall_watchdog,
                clock=Clock(clock_type=ClockType.STEADY_TIME))
        else:
            self.create_timer(.02, self._dispatch_tick, clock=Clock(clock_type=ClockType.STEADY_TIME))
        if self.clock_mode == 'relay100':
            from .ingress_dispatch import IngressDispatch
            if self.navigation_clock_dispatch is None:
                self.ingress_worker = IngressDispatch(self.context,
                    self.get_name()+'_ingress',self.get_namespace(),ingress_subscriptions)
            else:
                # The existing TimeSource callback and short input callbacks
                # share one serial receiver, started only after construction.
                self.ingress_worker = self.navigation_clock_dispatch
                try:
                    for args,kwargs in ingress_subscriptions:
                        kwargs={key:value for key,value in kwargs.items() if key!='callback_group'}
                        self.ingress_worker.node.create_subscription(*args,**kwargs)
                    self.ingress_worker.start()
                except BaseException:
                    self.ingress_worker.close()
                    super().destroy_node()
                    raise

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

    def _applied_reference(self,msg):
        receipt=time.monotonic_ns()
        try:
            stamp=msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
            if (msg.header.frame_id!='mujoco/pre_step' or stamp<0
                    or len(msg.name)!=len(msg.position) or len(set(msg.name))!=len(msg.name)
                    or not all(math.isfinite(value) for value in msg.position)):
                raise ValueError('invalid native application observation')
            sample=Sample(stamp,receipt,0,stamp,msg.header.frame_id,
                dict(name=tuple(msg.name),position=tuple(msg.position)))
            with self.inbox_lock:
                if self.closing:return
                previous=self._applied_pending.get(stamp)
                if previous is not None and previous.data!=sample.data:
                    raise ValueError('conflicting native application observation')
                self._applied_pending.setdefault(stamp,sample)
                while len(self._applied_pending)>16:del self._applied_pending[min(self._applied_pending)]
        except (ValueError,TypeError) as error:
            with self.inbox_lock:
                if self.active and self._ingress_fault is None:self._ingress_fault='applied:'+str(error)
        self._notify_reference_dispatch()

    def _notify_reference_dispatch(self):
        """Receiver hint only. The model owner still verifies every contract."""
        dispatch=getattr(self,'reference_dispatch',None)
        if dispatch is None:return
        trigger=False
        with self.inbox_lock:
            if self.closing or not dispatch.waiting:return
            ros_ns,wall_ns=self.get_clock().now().nanoseconds,time.monotonic_ns()
            hint=self.reference_retry_hint
            if hint is not None:
                found=False
                for sample in self._applied_pending.values():
                    if not (hint['issued_ros_ns']<=sample.stamp_ns<=ros_ns
                            and hint['issued_wall_ns']<=sample.received_ns<=wall_ns):continue
                    observed=dict(zip(sample.data['name'],sample.data['position']))
                    if (set(self.model.joint_names).issubset(observed)
                            and tuple(observed[name] for name in self.model.joint_names)==hint['values']):
                        found=True;break
                if not found:return
            trigger=dispatch.notify(ros_ns,wall_ns)
        if trigger:self.reference_retry_guard.trigger()

    def _retry_reference_tick(self):
        with self.inbox_lock:
            if self.closing or not self.reference_dispatch.take_notification():return
        self._dispatch_tick()

    def _schedule_reference_due(self):
        """One owned wall deadline; do not await the next coarse clock packet."""
        if self.reference_dispatch is None:return
        with self.inbox_lock:
            decision=self.reference_dispatch.last_decision
            due=(self.reference_dispatch.next_due_wall_ns
                if not self.closing and self.reference_dispatch.waiting and decision is not None else None)
            delay=0 if due is None else due-time.monotonic_ns()
            if delay<=0:
                self.reference_due_wall_ns=None
                if not self.reference_due_timer.is_canceled():self.reference_due_timer.cancel()
                return
            if self.reference_due_wall_ns==due and not self.reference_due_timer.is_canceled():return
            self.reference_due_wall_ns=due
            self.reference_due_timer.timer_period_ns=delay
            self.reference_due_timer.reset()

    def _reference_due_tick(self):
        with self.inbox_lock:
            due=self.reference_due_wall_ns
            now=time.monotonic_ns()
            if due is not None and now<due:
                # A superseded timer callback must not cancel the newer due.
                self.reference_due_timer.timer_period_ns=due-now
                self.reference_due_timer.reset()
                return
            self.reference_due_wall_ns=None
            self.reference_due_timer.cancel()
        self._notify_reference_dispatch()

    def _reference_permitted(self,command,ros_ns,wall_ns):
        if self.applied_credit is None:return True
        if command==(0.,0.,0.) or self.stop_reason or self.machine.stopping:
            self.applied_credit.suspend('stop_path');self._credit_motion=False
            return True
        owners=tuple(sorted(bytes(row.endpoint_gid) for row in
            self.get_publishers_info_by_topic('/navigation/applied_reference')))
        if len(owners)!=1 or self._applied_owner is not None and owners!=self._applied_owner:
            raise ValueError('applied_reference owner')
        self._applied_owner=owners
        with self.inbox_lock:
            eligible=[key for key,sample in self._applied_pending.items()
                if sample.stamp_ns<=ros_ns and sample.received_ns<=wall_ns]
            for key in sorted(eligible):self.applied_credit.receive(self._applied_pending.pop(key))
        return self.applied_credit.permit(ros_ns,wall_ns)

    def _gate(self, msg, info=None):
        entry_wall_ns = time.monotonic_ns()
        entry_system_ns = time.time_ns() if info is not None else None
        def field(name):
            return info.get(name) if isinstance(info, dict) else getattr(info, name, None)
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
                    received_ros_ns=self.get_clock().now().nanoseconds,
                    source_system_ns=field('source_timestamp'),
                    rmw_received_system_ns=field('received_timestamp'),
                    callback_system_ns=entry_system_ns))

    def _command(self, msg, info):
        receipt = time.monotonic_ns()
        receipt_ros = self.get_clock().now().nanoseconds
        warning = None
        with self.inbox_lock:
            if self.closing:return
            stepped=self.command_order.system_backstep
            accepted,reason=self.command_order.accept(info,self.cutoff_system)
            if not accepted:
                if reason.startswith('missing_') and self.active and self._ingress_fault is None:
                    self._ingress_fault = 'command:'+reason
                return
            source=self.command_order.last_source_system_ns
            if self.command_order.system_backstep and not stepped:
                warning = 'Final command SYSTEM clock backstep; DDS publication order retained; activation requires receiver restart: '+json.dumps(self.command_order.snapshot())
            self.last_command_source = source
            if any(v != 0. for v in (msg.linear.y, msg.linear.z, msg.angular.x, msg.angular.y)):
                if self.active and self._ingress_fault is None:
                    self._ingress_fault = 'nonplanar final command'
                return
            generation = self.gate.generation if self.gate is not None else -1
            self.command = Sample(receipt_ros, receipt,
                generation, source, 'nav_base', (msg.linear.x, 0., msg.angular.z))
            self.command_pending.append(self.command)
            self.command_receipts.append(dict(received_ns=receipt, received_ros_ns=receipt_ros,
                **self.command_order.snapshot()))
        if warning:self.get_logger().warning(warning)

    def _command_snapshot(self, ros_ns, wall_ns):
        with self.inbox_lock:
            # Callback entry is the immutable receipt boundary. A newer
            # concurrent/future receipt cannot replace this decision's input.
            candidates = [sample for sample in self.command_pending
                          if sample.stamp_ns <= ros_ns and sample.received_ns <= wall_ns]
            return candidates[-1] if candidates else None

    def _command_transport_snapshot(self):
        with self.inbox_lock:
            return self.command_order.snapshot()

    def on_configure(self, state):
        try:
            if self.ingress_worker is not None and self.ingress_worker.error:
                raise ValueError('ingress_dispatch:'+self.ingress_worker.error)
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
            self.applied_credit=(AppliedReferenceCredit(self.model.joint_names)
                if self.engine=='mujoco' and self.g2_validation_mode else None)
            self._credit_motion=False
            self.admission=(validate_profile(self.profile,self.model,self.engine) if self.execution_profile is None else
                validate_profile(self.profile,self.model,self.engine,execution_profile=self.execution_profile))
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
                if self.command_order.system_backstep:
                    self.get_logger().warning('activation rejected: command_clock_step_requires_restart')
                    return TransitionCallbackReturn.FAILURE
                if self._ingress_fault is not None:
                    return TransitionCallbackReturn.FAILURE
            ros_ns, wall_ns = self.get_clock().now().nanoseconds, time.monotonic_ns()
            self._select_gate(ros_ns,wall_ns=wall_ns)
            if self.machine is None or self.gate is None:
                return TransitionCallbackReturn.FAILURE
            with self.inbox_lock:
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
            self.stop_reason, self._stand_since = '', None
            self._last_stand_ready = False
            with self.inbox_lock:
                self.command = None
                self.command_pending.clear()
                self.cutoff_system, self.last_command_source = time.time_ns(), -1
                self.command_order=CommandOrder()
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
                if self.reference_dispatch is not None:self.reference_dispatch.cancel()
                self.reference_retry_hint=None
                if self.reference_due_timer is not None:
                    self.reference_due_timer.cancel();self.reference_due_wall_ns=None
            return super().on_deactivate(state)

    def on_cleanup(self, state):
        with self.lock:
            with self.inbox_lock:
                self.active = False
                if self.reference_dispatch is not None:self.reference_dispatch.cancel()
                self.reference_retry_hint=None
                if self.reference_due_timer is not None:
                    self.reference_due_timer.cancel();self.reference_due_wall_ns=None
                self._ingress_fault = None
                self.inbox.clear(self.get_clock().now().nanoseconds)
                self.gate = None
                self._gate_pending.clear()
            self.machine = None
            with self.inbox_lock:
                self.command = None
                self.command_pending.clear()
            return super().on_cleanup(state)

    def on_shutdown(self, state):
        with self.lock:
            with self.inbox_lock:
                self.active = False
                if self.reference_dispatch is not None:self.reference_dispatch.cancel()
                self.reference_retry_hint=None
                if self.reference_due_timer is not None:
                    self.reference_due_timer.cancel();self.reference_due_wall_ns=None
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
                command_receipts = list(self.command_receipts)
                reference_dispatch=self.reference_dispatch.snapshot() if self.reference_dispatch else None
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
                crawl_shift_reference_clock=machine._crawl_shift_clock,
                fault_stop_confirmed=machine.fault_stop_confirmed,
                simulation_control_cadence=self.simulation_cadence,
                reference_dispatch=reference_dispatch,
                crawl_swing_reference_clock=machine._crawl_swing_clock,
                applied_reference_credit=self.applied_credit.snapshot() if self.applied_credit else None,
                reference_body=machine.reference_body.tolist(),
                targets={key: value.tolist() for key, value in getattr(machine, '_targets', {}).items()},
                floor=dict(getattr(machine, 'floor', {})),
                last_published_leg_targets=dict(self._held_targets or {}),
                selected_body=selected['body'], selected_contacts=selected['contacts'])
            response.success = True
            response.message = json.dumps(dict(model_sha256=self.model.model_sha256 if self.model else '',
                generation=self.generation, active=self.active, first_fault=self.first_fault,
                ingress_dispatch=self.ingress_worker.snapshot() if self.ingress_worker else None,
                first_stop=self.first_stop, current=current,command_transport=self._command_transport_snapshot(),
                command_receipts=command_receipts,
                decision_cost_trace=list(self.decision_cost_trace),
                command_publications=dict(capacity=512, total=self.command_publication_count,
                    joint_names=list(self.model.joint_names) if self.model else [],
                    rows=list(self.command_publications))), allow_nan=False)
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
        status.stopped = self.active and (stand_ready or status.state == 'STOPPED'
            or status.state=='FAULT' and self.machine.fault_stop_confirmed)
        self.status.publish(status)

    def _control_wall_watchdog(self):
        if self.closing or time.monotonic_ns()-self.last_control_dispatch_wall_ns<=200_000_000:
            return
        if self.active:
            # A watchdog dispatch must never advance a moving reference even
            # if a very slow clock advanced by less than one control period.
            with self.inbox_lock:
                self._ingress_fault=self._ingress_fault or 'control_dispatch_wall_timeout'
        self._dispatch_tick()

    def _periodic_control_tick(self):
        """Do not spend the reserved control period on an early ROS wake.

        The source clock may run ahead of the independent wall period. A
        reserved owner decision already has its cancellable wall notification;
        keep that reservation instead of cancelling it and doing work which
        the reference rate gate will refuse. No sensor/ACK age is renewed.
        Stop/fault/lifecycle and the independent watchdog retain their paths.
        """
        if (self.active and self._credit_motion and not self.stop_reason
                and self.machine is not None and self.machine.state=='CRAWL'
                and not self.machine.stopping):
            with self.inbox_lock:
                dispatch=self.reference_dispatch
                if (dispatch is not None and dispatch.waiting
                        and dispatch.last_decision is not None
                        and time.monotonic_ns()<dispatch.next_due_wall_ns):
                    return
        self._dispatch_tick()

    def _dispatch_tick(self):
        started = time.monotonic_ns()
        if self.simulation_cadence:
            self._decision_cost_current=dict(started_wall_ns=started,stages=[],
                started_thread_ns=time.thread_time_ns(),native_tid=threading.get_native_id(),
                publication_before=self.command_publication_count)
        self.last_control_dispatch_wall_ns=started
        if self.reference_dispatch is not None:
            with self.inbox_lock:self.reference_dispatch.begin_tick()
        self.tick_dispatch_started_ns = started
        try:
            if self.ingress_worker is not None and self.ingress_worker.error:
                with self.inbox_lock:
                    if self._ingress_fault is None:
                        self._ingress_fault='ingress_dispatch:'+self.ingress_worker.error
            self._tick()
        finally:
            finished=time.monotonic_ns()
            if self._decision_cost_current is not None:
                self._decision_cost_current.update(finished_wall_ns=finished,
                    finished_thread_ns=time.thread_time_ns(),
                    state=getattr(self.machine,'state',None),
                    publication_after=self.command_publication_count)
                self.decision_cost_trace.append(self._decision_cost_current)
                self._decision_cost_current=None
            self.tick_spans.append(dict(started_ns=started, finished_ns=finished,
                                        ros_ns=self.get_clock().now().nanoseconds))
            self._schedule_reference_due()
            self._notify_reference_dispatch()

    def _mark_decision_cost(self,stage):
        # Bounded numeric-only observation in the existing single owner.
        # No profiler, file write, new worker, clock replacement or permission.
        if self._decision_cost_current is not None:
            self._decision_cost_current['stages'].append((stage,time.monotonic_ns(),time.thread_time_ns()))

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
            if self._decision_cost_current is not None:
                self._decision_cost_current['decision_ros_ns']=ros_ns
            self._mark_decision_cost('clock')
            bundle = self._bundle_snapshot(ros_ns,wall_ns)
            self._mark_decision_cost('bundle')
            selected_command = self._command_snapshot(ros_ns,wall_ns)
            self._mark_decision_cost('command')
            with self.inbox_lock:
                if self._ingress_fault is not None:
                    self.machine._fail(self._ingress_fault)
            if self.count_publishers('/leg_position_controller/commands') != 1:
                self.machine._fail('owner:legs')
            self._mark_decision_cost('leg_owner')
            valid, reason = self._gate_valid(ros_ns, wall_ns)
            self._mark_decision_cost('guard')
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
                if self.validation_mode and not self.g2_validation_mode:
                    self.machine._fail('validation_mode_forbids_crawl')
                elif not self.admission[0]:
                    self.machine._fail(self.admission[1])
                else:
                    fresh, why = sample_valid(selected_command, ros_ns, wall_ns, self.generation, max_age_ns=200_000_000)
                    if not fresh:
                        self.stop_reason = 'final_command:'+why
                        self.machine.request_stop(urgent=True)
                    else:
                        command = selected_command.data
            elif self.machine.state == 'CRAWL':
                self.machine.request_stop(urgent=self.gate is None or bool(self.gate.fault_reason))
            self._mark_decision_cost('command_gate')
            reference_permitted=True
            if self.applied_credit is not None:
                if command!=(0.,0.,0.) and not self.stop_reason and not self.machine.stopping:
                    if not self._credit_motion:
                        self.applied_credit.prime(self._held_targets[name] for name in self.model.joint_names)
                        self._credit_motion=True
                try:
                    reference_permitted=self._reference_permitted(command,ros_ns,wall_ns)
                except (ValueError,KeyError,TypeError) as error:
                    self.stop_reason=self.stop_reason or 'applied_reference:'+str(error)
                    self.machine.request_stop(urgent=True)
                    self.applied_credit.suspend('fault_stop');self._credit_motion=False
            self._mark_decision_cost('native_credit')
            paced_motion=(self.reference_dispatch is not None and self._credit_motion
                and command!=(0.,0.,0.) and not self.stop_reason and not self.machine.stopping)
            if paced_motion:
                with self.inbox_lock:
                    reference_permitted=reference_permitted and self.reference_dispatch.allowed(ros_ns,wall_ns)
            if self._decision_cost_current is not None:
                self._decision_cost_current['reference_permitted']=reference_permitted
            self._mark_decision_cost('reference_rate')
            if self.stop_reason and self.first_stop is None:
                with self.inbox_lock:
                    guard_receipts = list(self.guard_receipts)
                    command_receipts = list(self.command_receipts)
                guard = None if self.gate is None else dict(
                    stamp_ns=self.gate.header.stamp.sec*1_000_000_000+self.gate.header.stamp.nanosec,
                    received_ns=self.gate_receipt, state=self.gate.state,
                    generation=self.gate.generation, model_sha256=self.gate.model_sha256,
                    ready=self.gate.ready, fault_reason=self.gate.fault_reason)
                self.first_stop = dict(scope='first_tick_observing_stop_reason', reason=self.stop_reason,
                    ros_ns=ros_ns, wall_ns=wall_ns, guard=guard, samples=asdict(bundle),
                    selected_command=asdict(selected_command) if selected_command else None,
                    command_transport=self._command_transport_snapshot(),
                    command_receipts=command_receipts,
                    guard_receipts=guard_receipts, tick_spans=list(self.tick_spans),
                    held_targets=dict(self._held_targets), state=self.machine.state)
            before = dict(state=self.machine.state, phase=self.machine.phase,
                          swing_foot=self.machine.swing_foot)
            result = self.machine.advance(bundle, command, ros_ns, wall_ns,
                reference_permitted=reference_permitted)
            self._mark_decision_cost('model')
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
                        decision_cost_current=deepcopy(self._decision_cost_current),
                        state_before=before, transition_during_advance=before['state'] != 'FAULT',
                        reference_body=self.machine.reference_body.tolist(),
                        targets={name: value.tolist() for name, value in self.machine._targets.items()},
                        phase_context={name: getattr(self.machine, name, None) for name in
                            ('_phase_start', '_shift_duration', '_shift_settled_start', '_unload_start')})
                waiting=(paced_motion and not reference_permitted and result.state=='CRAWL'
                    and not self.machine.stopping)
                if self.reference_dispatch is not None:
                    if waiting:
                        self.reference_retry_hint=deepcopy(self.applied_credit.pending)
                        self.reference_dispatch.defer()
                    else:
                        self.reference_dispatch.cancel();self.reference_retry_hint=None
                if result.joint_targets is not None and not waiting:
                    values = [result.joint_targets[n] for n in self.model.joint_names]
                    publish_started = time.monotonic_ns()
                    self.legs.publish(Float64MultiArray(data=values))
                    publish_finished = time.monotonic_ns()
                    if self.applied_credit is not None and self._credit_motion and not self.stop_reason:
                        self.applied_credit.submitted(values,ros_ns,publish_started)
                    if paced_motion:
                        self.reference_dispatch.issued(ros_ns,wall_ns)
                        # Reserve the next computation immediately. ACK and
                        # original ROS progress still gate the owner callback.
                        self.reference_retry_hint=deepcopy(self.applied_credit.pending)
                        self.reference_dispatch.defer()
                    self.command_publication_count += 1
                    self.command_publications.append(dict(sequence=self.command_publication_count,
                        decision_ros_ns=ros_ns, decision_wall_ns=wall_ns,
                        publish_started_ns=publish_started, publish_finished_ns=publish_finished,
                        generation=self.generation, values=values))
                    # Preserve this owner's spring preload across inactivity.
                    self._held_targets = dict(result.joint_targets)
                    ready = self._stand_ready(bundle, result, wall_ns)
            self._mark_decision_cost('publication')
            self._last_stand_ready = ready
            self._publish_status(result, ready)
            self._mark_decision_cost('status')

    def destroy_node(self):
        with self.lock:
            with self.inbox_lock:
                self.closing, self.active = True, False
                if self.reference_dispatch is not None:self.reference_dispatch.cancel()
                self.reference_retry_hint=None
                if self.reference_due_timer is not None:
                    self.reference_due_timer.cancel();self.reference_due_wall_ns=None
        if self.ingress_worker is not None:
            self.ingress_worker.close()
            self.get_logger().info('Navigation ingress closed: '+json.dumps(self.ingress_worker.snapshot()))
        return super().destroy_node()


def main(args=None):
    from .clock_execution import run_control_node
    run_control_node(CrawlController,args=args)
