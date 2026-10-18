"""ROS glue for explicitly enabled, small-angle, stationary-base camera tracking.

This is not a collision planner, whole-body controller, or physical grasp policy.
All arm motion passes through the manipulation node's single action owner.
"""
from collections import deque
import json
import math
import time
from xml.etree.ElementTree import ParseError

from action_msgs.msg import GoalStatusArray
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import PointStamped
from integrated_robot_interfaces.msg import TrackedTarget
from integrated_robot_vision.cache import nanoseconds, parse_intrinsics
from integrated_robot_vision.contracts import covariance
from integrated_robot_vision.kinematics import KinematicChain
from integrated_robot_vision.servo import servo_target
import numpy as np
from rclpy.clock import Clock, ClockType
from rclpy.duration import Duration
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import String
from std_srvs.srv import SetBool, Trigger
from tf2_geometry_msgs import do_transform_point
from tf2_ros import Buffer, TransformListener, TransformException
from trajectory_msgs.msg import JointTrajectoryPoint

from .policy import ARM_NAMES, LEG_NAMES, STAND, joint_snapshot
from .visual_tracking import VisualTrackingGuard


class TrackingSupport:
    def __init__(self, node):
        self.node = node
        self.guard = VisualTrackingGuard()
        self.chain = self.model_text = self.k = self.target = None
        self.joints = deque(maxlen=32)
        self.legs = {}
        self.legs_at = self.info_at = self.target_at = 0.
        self.info_stamp = 0
        self.foreign = False
        self.session = False
        self.record = None
        self.token = None
        self.reference = None
        self.last_dispatch = -math.inf
        self.goal_count = 0
        self.last_ros = None
        self.advanced_at = time.monotonic()
        self.buffer = Buffer(node=node)
        self.listener = TransformListener(self.buffer, node)
        group = node.group
        model_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        node.create_subscription(String, '/robot_description', self.on_model, model_qos,
                                 callback_group=group)
        node.create_subscription(CameraInfo, '/camera/color/camera_info', self.on_info, qos_profile_sensor_data,
                                 callback_group=group)
        node.create_subscription(TrackedTarget, '/vision/tracked_target', self.on_target, 10,
                                 callback_group=group)
        node.create_subscription(String, '/architecture/locomotion', self.on_legs, 10,
                                 callback_group=group)
        node.create_subscription(GoalStatusArray,
                                 '/arm_trajectory_controller/follow_joint_trajectory/_action/status',
                                 self.on_status, model_qos, callback_group=group)
        node.create_service(SetBool, '~/set_visual_tracking', self.toggle, callback_group=group)
        node.create_service(Trigger, '~/recover_arm_ownership', self.recover, callback_group=group)
        self.status = node.create_publisher(String, '/architecture/visual_tracking', 10)
        self.timer = node.create_timer(.02, self.tick, callback_group=group,
                                       clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.last_report = 0.

    def on_model(self, message):
        with self.node.lock:
            if message.data == self.model_text:
                return
            self.disable('robot model changed')
            self.model_text = message.data
            try:
                self.chain = KinematicChain.from_urdf(message.data)
                if self.chain.joint_names != ARM_NAMES:
                    raise ValueError('six canonical arm joints required')
            except (ValueError, TypeError, ParseError):
                self.chain = None

    def on_info(self, message):
        with self.node.lock:
            try:
                k = parse_intrinsics(message)
                stamp = nanoseconds(message.header.stamp)
                if k.frame_id != 'camera_optical_frame' or stamp <= 0:
                    raise ValueError('optical frame and nonzero stamp required')
                if self.k is not None and k.calibration_id != self.k.calibration_id:
                    self.disable('camera calibration changed')
                self.k, self.info_stamp, self.info_at = k, stamp, time.monotonic()
            except (ValueError, TypeError):
                self.k = None
                self.disable('invalid camera calibration')

    def on_target(self, message):
        with self.node.lock:
            try:
                stamp = nanoseconds(message.header.stamp)
                source_stamp = nanoseconds(message.source_header.stamp)
                p = message.position
                covariance(np.array(message.covariance).reshape(3, 3))
                if (not message.valid or message.status != 'TRACKED' or stamp <= 0
                        or source_stamp != stamp or message.header.frame_id != 'odom'
                        or message.source_header.frame_id != 'camera_optical_frame'
                        or not message.track_id or not message.class_id
                        or not .5 <= message.score <= 1.
                        or not all(math.isfinite(v) for v in (p.x, p.y, p.z))):
                    raise ValueError('invalid/lost target')
                if self.target is not None:
                    if message.track_id != self.target.track_id:
                        self.disable('target identity changed')
                    if stamp <= nanoseconds(self.target.header.stamp):
                        return  # duplicates never renew wall-clock validity
                self.target, self.target_at = message, time.monotonic()
            except (ValueError, TypeError):
                self.target = None
                self.disable('invalid/lost target')

    def on_joints(self, message):
        try:
            stamp = nanoseconds(message.header.stamp)
            arm = joint_snapshot(message.name, message.position, ARM_NAMES)
            legs = joint_snapshot(message.name, message.position, LEG_NAMES)
            if stamp <= 0 or arm is None or legs is None:
                raise ValueError('incomplete measured joints')
            if self.joints and stamp <= self.joints[-1][0]:
                return
            self.joints.append((stamp, time.monotonic(), dict(zip(ARM_NAMES, arm)), legs))
        except (ValueError, TypeError):
            self.joints.clear()
            self.disable('invalid joints')

    def on_legs(self, message):
        with self.node.lock:
            try:
                value = json.loads(message.data)
                self.legs = value if isinstance(value, dict) else {}
            except (ValueError, TypeError):
                self.legs = {}
            self.legs_at = time.monotonic()

    def on_status(self, message):
        with self.node.lock:
            self.foreign = any(self.node.arm_owner.is_foreign(bytes(v.goal_info.goal_id.uuid),
                                                              v.status) for v in message.status_list)
            if self.foreign:
                self.disable('unknown live arm trajectory goal')

    def conditions(self, now, wall):
        node = self.node
        joint = self.joints[-1] if self.joints else None
        target_stamp = nanoseconds(self.target.header.stamp) if self.target else 0
        return dict(
            active=node.enabled, arm_safe=node.measured_safe(),
            joints_fresh=bool(joint and 0 <= wall-joint[1] <= .3
                              and -.03e9 <= now-joint[0] <= .3e9),
            target_valid=self.target is not None,
            target_fresh=bool(self.target and -.03e9 <= now-target_stamp <= .3e9
                              and 0 <= wall-self.target_at <= .3),
            model_ready=self.chain is not None,
            camera_ready=bool(self.k and -.03e9 <= now-self.info_stamp <= 1e9
                              and 0 <= wall-self.info_at <= 1.),
            legs_standing=bool(joint and all(abs(a-b) <= .15 for a, b in zip(joint[3], STAND))
                               and self.legs.get('active') is True
                               and self.legs.get('ready') is True
                               and self.legs.get('mode') in ('STAND', 'HOLD', 'STOP')
                               and 0 <= wall-self.legs_at <= .5),
            arm_free=bool((self.session or not node.busy) and not node.arm_owner.fault),
            no_external_producer=not self.foreign and node.count_publishers(
                '/arm_trajectory_controller/joint_trajectory') == 0,
            action_ready=node.trajectory.server_is_ready(),
            clock_valid=now > 0 and wall-self.advanced_at <= .3)

    def toggle(self, request, response):
        with self.node.lock:
            if not request.data:
                self.disable('operator disable')
                response.success, response.message = True, 'Tracking OFF; own cancel may be pending'
                return response
            conditions = self.conditions(self.node.get_clock().now().nanoseconds, time.monotonic())
            conditions['arm_safe'] = conditions['arm_safe'] and self.node.safe
            try:
                self.token = self.guard.enable(conditions)
                self.session = self.node.busy = True
                self.reference = self.joints[-1][2].copy()
                response.success, response.message = True, 'Explicit stationary local tracking enabled'
            except ValueError as exc:
                response.message = str(exc) + ': ' + ','.join(k for k, v in conditions.items() if not v)
            return response

    def disable(self, reason):
        self.guard.disable(reason)
        if self.session:
            self.node.arm_owner.cancel(now=time.monotonic())
        self._release()

    def _release(self):
        if self.record is not None and self.record.terminal:
            result = self.record.result
            if self.guard.enabled and (result is None or result.status != 4
                    or result.result.error_code != FollowJointTrajectory.Result.SUCCESSFUL):
                self.guard.disable('tracking trajectory failed or rejected')
            self.guard.complete(self.token)
            self.record = None
        if self.session and not self.guard.enabled and self.node.arm_owner.pending is None:
            if not self.node.arm_owner.fault and not self.guard.fault:
                self.session = False
                self.node.busy = self.node.work_running

    def recover(self, request, response):
        with self.node.lock:
            if (self.guard.enabled or not self.node.measured_safe() or self.foreign
                    or self.node.count_publishers('/arm_trajectory_controller/joint_trajectory')):
                response.message = 'Disable first; fresh safe arm and no external producer required'
                return response
            if self.node.arm_owner.recover() and self.guard.recover(acknowledged=True):
                self._release()
                self.node.busy = self.node.work_running
                response.success = True
                response.message = 'Terminal action confirmed; ownership fault explicitly cleared'
            else:
                response.message = 'Action acceptance/result remains unknown; reservation retained'
            return response

    def current_goal(self, now, wall):
        target = PointStamped(header=self.target.header, point=self.target.position)
        # Latest measured joint with a transform at THAT exact joint stamp. Never latest TF.
        for stamp, received, q, _ in reversed(self.joints):
            if not (0 <= wall-received <= .3 and -.03e9 <= now-stamp <= .3e9):
                continue
            try:
                transform = self.buffer.lookup_transform('base_link', 'odom',
                    Time(nanoseconds=stamp, clock_type=self.node.get_clock().clock_type),
                    timeout=Duration(seconds=0.))
                point = do_transform_point(target, transform).point
                values = servo_target(self.chain, q, np.array([point.x, point.y, point.z]), self.k, .2)
                if values is None:
                    return None
                for name in ARM_NAMES:
                    if name not in ('arm_joint_1', 'arm_joint_5'):
                        values[name] = self.reference[name]
                return values
            except TransformException:
                continue
        return None

    def tick(self):
        with self.node.lock:
            node, wall = self.node, time.monotonic()
            now = node.get_clock().now().nanoseconds
            if self.last_ros is not None and now < self.last_ros:
                self.disable('clock rollback')
                self.target = None
                self.joints.clear()
                self.buffer.clear()
            if self.last_ros is None or now > self.last_ros:
                self.advanced_at = wall
            self.last_ros = now
            node.arm_owner.watchdog(now=wall)
            if node.arm_owner.fault and self.session:
                self.guard.latch_fault(node.arm_owner.fault)
            self._release()
            if not self.session and not node.work_running:
                node.busy = node.arm_owner.pending is not None or bool(node.arm_owner.fault)
            if self.guard.enabled:
                conditions = self.conditions(now, wall)
                if not all(conditions.values()):
                    self.disable('safety gate lost: '+','.join(k for k, v in conditions.items() if not v))
                elif self.record is None and wall-self.last_dispatch >= .2:
                    values = self.current_goal(now, wall)
                    if values is None:
                        self.disable('current-time TF, visibility or Jacobian unavailable')
                    elif self.guard.reserve(self.token):
                        goal = FollowJointTrajectory.Goal()
                        goal.trajectory.joint_names = list(ARM_NAMES)
                        point = JointTrajectoryPoint(positions=[values[n] for n in ARM_NAMES])
                        point.time_from_start.nanosec = 200_000_000
                        goal.trajectory.points = [point]
                        node.safe = False
                        self.record = node.arm_owner.send(goal, now=wall, timeout=1.)
                        self.last_dispatch, self.goal_count = wall, self.goal_count+1
            if self.record is None and self.session and not node.arm_owner.fault:
                node.safe = node.measured_safe()
            if wall-self.last_report >= .2:
                self.status.publish(String(data=json.dumps(dict(
                    enabled=self.guard.enabled, reason=self.guard.reason, goal_count=self.goal_count,
                    reserved=node.busy, outstanding=node.arm_owner.pending is not None,
                    fault=node.arm_owner.fault or self.guard.fault, generation=self.guard.generation))))
                self.last_report = wall
