"""One actual arm-action lease plus measured unloaded carry; never grasp proof."""
import json
from collections import deque
from dataclasses import asdict
from pathlib import Path
import threading
import time

from action_msgs.msg import GoalStatusArray
from control_msgs.action import FollowJointTrajectory
from rclpy.node import Node
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectoryPoint
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_runtime.arm_action_owner import ArmActionOwner
from integrated_robot_runtime.arm_transport import ArmActionTransport

from .carry_profile import CarryProfile, _validate_limits, swept_footprint
from .model import compile_model
from .observations import SensorInbox, sensor_sample
from .samples import Sample, sample_valid


class CarryManager(Node):
    ARM = tuple('arm_joint_'+str(i) for i in range(1, 7))
    GRIPPER = ('gripper_left_joint', 'gripper_right_joint')
    GRIPPER_ERROR_M = .002
    GRIPPER_VELOCITY_MPS = .005
    ARM_TOPIC = '/arm_trajectory_controller/joint_trajectory'
    GRIPPER_TOPIC = '/gripper_position_controller/commands'
    STATUS_TOPIC = '/arm_trajectory_controller/follow_joint_trajectory/_action/status'

    def __init__(self, model=None, profile=None, **kwargs):
        super().__init__('carry_manager', **kwargs)
        try:
            model_file = self.declare_parameter('model_file', '').value
            profile_file = self.declare_parameter('carry_profile', '').value
            self.declare_parameter('validation_mode', False)
            self.model = model or compile_model(Path(model_file).read_text())
            self.profile = profile or CarryProfile(**json.loads(Path(profile_file).read_text()))
            _validate_limits(self.profile.limits)
            swept_footprint(self.model, self.profile, self.profile.limits)
            if len(self.profile.arm_q) != 6 or any(not self.model.limits[n][0] <= q <= self.model.limits[n][1]
                                                  for n, q in zip(self.ARM, self.profile.arm_q)):
                raise ValueError('invalid model carry target')
        except Exception:
            super().destroy_node()
            raise
        self.lock = threading.RLock()
        self.inbox = SensorInbox(0)
        self.observed = {key: {} for key in ('guard', 'crawl')}
        self.selected = dict.fromkeys(self.observed)
        self.state, self.fault = 'IDLE', ''
        self.first_fault = None
        self.generation, self.record = 0, None
        self.closing = False
        self.settled_since = None
        self.started_at = 0.
        self.owner_ids = None
        self.diagnostics = deque(maxlen=32)
        self.status = self.create_publisher(MotionState, '/navigation/carry_state', 10)
        self.gripper = self.create_publisher(Float64MultiArray, self.GRIPPER_TOPIC, 10)
        self.create_subscription(JointState, '/joint_states', self._joints, qos_profile_sensor_data)
        for key in self.observed:
            self.create_subscription(MotionState, '/navigation/'+key+'_state',
                lambda msg, stream=key: self._observation(stream, msg), 10)
        self.create_subscription(GoalStatusArray, self.STATUS_TOPIC, self._action_status,
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_service(Trigger, '~/prepare', self._prepare)
        self.create_service(Trigger, '~/stop', self._stop)
        self.create_service(Trigger, '~/report', self._report)
        self.create_timer(.02, self._tick, clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.transport = ArmActionTransport(self)
        self.owner = ArmActionOwner(self.transport.client)
        try:
            self.transport.start()
        except Exception:
            self.transport.close()
            super().destroy_node()
            raise

    def _joints(self, msg):
        try:
            sample = sensor_sample('joints', msg, time.monotonic_ns(), 0)
            with self.lock:
                if not self.closing:
                    self.inbox.receive('joints', sample)
        except (ValueError, TypeError) as error:
            with self.lock:
                if self.record is not None:
                    self._fail('joints:'+str(error))

    def _observation(self, key, msg):
        stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        with self.lock:
            if self.closing:
                return
            previous = self.selected[key]
            if previous is not None and stamp <= previous.stamp_ns:
                return
            data = dict(state=msg.state, ready=msg.ready, stopped=msg.stopped,
                        generation=msg.generation, model_sha256=msg.model_sha256, fault=msg.fault_reason)
            self.diagnostics.append(dict(event='receive', stream=key,
                source_age_ms=(self.get_clock().now().nanoseconds-stamp)/1e6))
            self.observed[key].setdefault(stamp, Sample(stamp, time.monotonic_ns(), 0, stamp,
                                                      msg.header.frame_id, data))
            while len(self.observed[key]) > 10:
                del self.observed[key][min(self.observed[key])]

    def _state_sample(self, key, ros_ns):
        pending = self.observed[key]
        eligible = [stamp for stamp in pending if stamp <= ros_ns]
        if eligible:
            latest = max(eligible)
            self.selected[key] = pending[latest]
            for stamp in list(pending):
                if stamp <= latest:
                    del pending[stamp]
        return self.selected[key]

    def _action_status(self, msg):
        with self.lock:
            if any(self.owner.is_foreign(bytes(row.goal_info.goal_id.uuid), row.status)
                   for row in msg.status_list):
                self._fail('foreign arm action owner')

    def _owners(self):
        started = time.monotonic_ns()
        topics = ('/navigation/guard_state', '/navigation/crawl_state', '/joint_states', self.STATUS_TOPIC,
                  self.GRIPPER_TOPIC)
        ids = tuple(tuple(sorted(bytes(p.endpoint_gid) for p in self.get_publishers_info_by_topic(topic)))
                    for topic in topics)
        arm_count = self.count_publishers(self.ARM_TOPIC)
        self.diagnostics.append(dict(event='owners', elapsed_ms=(time.monotonic_ns()-started)/1e6,
                                     counts=list(map(len, ids)), arm_count=arm_count))
        if any(len(value) != 1 for value in ids) or arm_count:
            raise ValueError('duplicate/missing arm or observation owner: '+str(
                dict(zip(topics, map(len, ids))))+' arm_topic='+str(arm_count))
        if self.owner_ids is not None and ids != self.owner_ids:
            raise ValueError('carry owner identity changed')
        return ids

    def _feedback(self, ros_ns, wall_ns, *, starting=False):
        values = {}
        for key in ('guard', 'crawl'):
            sample = self._state_sample(key, ros_ns)
            ok, why = sample_valid(sample, ros_ns, wall_ns, 0, max_age_ns=200_000_000)
            if not ok:
                self.diagnostics.append(dict(event='invalid_observation', stream=key, reason=why,
                    ros_age_ms=(ros_ns-sample.stamp_ns)/1e6 if sample else None,
                    wall_age_ms=(wall_ns-sample.received_ns)/1e6 if sample else None))
                raise ValueError(key+':'+why)
            data = sample.data
            if data['model_sha256'] != self.model.model_sha256 or data['fault']:
                raise ValueError(key+':model/fault')
            values[key] = data
        if starting:
            if (values['guard']['state'] not in ('STAND', 'HOLD')
                    or values['crawl']['state'] not in ('STAND', 'STOPPED')
                    or not values['crawl']['ready'] or not values['crawl']['stopped']):
                raise ValueError('measured STAND required before carry')
            generation = values['guard']['generation']
        else:
            generation = self.generation
        if any(data['generation'] != generation for data in values.values()):
            raise ValueError('carry generation changed')
        sample = self.inbox.bundle(ros_ns).joints
        ok, why = sample_valid(sample, ros_ns, wall_ns, 0, max_age_ns=200_000_000)
        if not ok:
            raise ValueError('joints:'+why)
        q, qd = sample.data['position'], sample.data['velocity']
        if set(q) != set(self.model.limits) or set(qd) != set(q):
            raise ValueError('joint model names')
        if any(not lo <= q[name] <= hi or abs(qd[name]) > speed
               for name, (lo, hi, speed, _) in self.model.limits.items()):
            raise ValueError('joint physical bounds')
        return generation, q, qd

    def _prepare(self, request, response):
        with self.lock:
            if self.closing or self.fault or self.record is not None or not self.transport.healthy:
                response.message = self.fault or 'carry busy/closing'
                return response
            try:
                generation, _, _ = self._feedback(self.get_clock().now().nanoseconds,
                                                   time.monotonic_ns(), starting=True)
                ids = self._owners()
                if not self.transport.client.server_is_ready():
                    raise ValueError('arm action server unavailable')
                goal = FollowJointTrajectory.Goal()
                goal.trajectory.joint_names = list(self.ARM)
                goal.trajectory.points = [JointTrajectoryPoint(positions=list(self.profile.arm_q))]
                goal.trajectory.points[0].time_from_start.sec = 3
                self.generation, self.owner_ids = generation, ids
                self.started_at = time.monotonic()
                self.record = self.owner.send(goal, now=self.started_at, timeout=8.)
                self.state = 'MOVING'
                response.success, response.message = True, 'carry lease reserved; readiness awaits actual result and settle'
            except (ValueError, RuntimeError) as error:
                response.message = str(error)
        return response

    def _fail(self, reason):
        if self.first_fault is None:
            sample = self.inbox.samples['joints']
            self.first_fault = dict(scope='selected_cache_at_first_failure', reason=reason,
                ros_ns=self.get_clock().now().nanoseconds, wall_ns=time.monotonic_ns(),
                state_before=self.state, model_sha256=self.model.model_sha256, generation=self.generation,
                selected_joint_sample=asdict(sample) if sample else None,
                selected_motion={key: asdict(value) if value else None
                                 for key, value in self.selected.items()})
        self.fault = self.fault or reason
        self.state, self.settled_since = 'FAULT', None
        self.owner.cancel(now=time.monotonic())

    def _stop(self, request, response):
        with self.lock:
            self.closing = True
            if not self.fault:
                self.state = 'STOPPING'
            self.owner.cancel(now=time.monotonic())
            response.success, response.message = True, 'new commands blocked; terminal result drain required'
            return response

    def _report(self, request, response):
        with self.lock, self.owner.lock:
            record = self.record
            value = self.owner.snapshot()
            result = record.result if record else None
            value.update(uuid=record.identifier.hex() if record else None,
                terminal=bool(record and record.terminal), result_status=result.status if result else None,
                result_error_code=result.result.error_code if result else None,
                generation=self.generation, model_sha256=self.model.model_sha256,
                receiver_healthy=self.transport.healthy, state=self.state, fault=self.fault,
                first_fault=self.first_fault)
            # Owner.snapshot refers to pending. After a real terminal it is empty,
            # but the completed record still owns the received typed future.
            value['result_future_done'] = bool(record and record.result_future is not None
                                                and record.result_future.done())
            response.success, response.message = True, json.dumps(value, allow_nan=False)
            return response

    def _tick(self):
        with self.lock:
            now, wall_ns, ros_ns = time.monotonic(), time.monotonic_ns(), self.get_clock().now().nanoseconds
            self.owner.watchdog(now=now)
            if self.owner.fault:
                self._fail(self.owner.fault)
            if self.record is not None and not self.closing and not self.fault:
                try:
                    _, q, qd = self._feedback(ros_ns, wall_ns)
                    self._owners()
                    if not self.transport.healthy:
                        raise ValueError('arm result receiver unhealthy')
                    self.gripper.publish(Float64MultiArray(data=[.015, .015]))
                    record = self.record
                    if record.terminal:
                        if (record.result is None or record.result.status != 4
                                or record.result.result.error_code != FollowJointTrajectory.Result.SUCCESSFUL):
                            raise ValueError('actual carry terminal failed/rejected')
                        target = dict(zip(self.ARM, self.profile.arm_q))
                        arm_settled = all(abs(q[n]-v) <= self.profile.limits['carry_error_rad']
                                          and abs(qd[n]) <= self.profile.limits['carry_velocity_rps']
                                          for n, v in target.items())
                        gripper_settled = all(abs(q[n]-.015) <= self.GRIPPER_ERROR_M
                                              and abs(qd[n]) <= self.GRIPPER_VELOCITY_MPS
                                              for n in self.GRIPPER)
                        settled = arm_settled and gripper_settled
                        if not settled:
                            self.settled_since = None
                            if self.state == 'READY':
                                raise ValueError('measured carry posture lost')
                        elif self.settled_since is None:
                            self.settled_since = now
                        if self.settled_since is not None and now-self.settled_since >= 1.:
                            self.state = 'READY'
                        elif self.state != 'READY':
                            self.state = 'SETTLING'
                        if self.state != 'READY' and now-self.started_at > 11.:
                            raise ValueError('carry measured settle timeout')
                except (ValueError, KeyError, TypeError) as error:
                    self._fail(str(error))
            msg = MotionState(generation=self.generation, model_sha256=self.model.model_sha256,
                              state=self.state, ready=self.state == 'READY' and not self.closing,
                              fault_reason=self.fault)
            msg.header.stamp, msg.header.frame_id = self.get_clock().now().to_msg(), 'base_link'
            self.status.publish(msg)

    def begin_shutdown(self):
        self._stop(None, Trigger.Response())

    def shutdown_ready(self):
        return self.owner.pending is None

    def destroy_node(self):
        self.begin_shutdown()
        if not self.shutdown_ready():
            raise RuntimeError('carry terminal unconfirmed; action receiver and ROS handles retained')
        self.transport.close()
        return super().destroy_node()


def main(args=None):
    from integrated_robot_runtime.common import spin
    spin(CarryManager, threads=1)
