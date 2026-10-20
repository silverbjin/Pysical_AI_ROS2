"""Measured arm startup and explicit, cancelable PickObject protocol rehearsal."""
import math
import threading
import time

from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from integrated_robot_interfaces.action import PickObject
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from sensor_msgs.msg import JointState
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectoryPoint

from .common import seconds, spin
from .policy import ARM_NAMES, SAFE_ARM, joint_snapshot, safe_arm, validate_target
from .arm_action_owner import ArmActionOwner
from .tracking_support import TrackingSupport


class ManipulationNode(LifecycleNode):
    def __init__(self, **kwargs):
        super().__init__('manipulation_node', **kwargs)
        self.lock = threading.RLock()
        self.enabled = False
        self.busy = False
        self.work_running = False
        self.safe = False
        self.arm = None
        self.received = self.stamp = 0.0
        self.group = ReentrantCallbackGroup()
        self.create_subscription(JointState, '/joint_states', self.on_joints, 10,
                                 callback_group=self.group)
        self.trajectory = ActionClient(self, FollowJointTrajectory,
                                       '/arm_trajectory_controller/follow_joint_trajectory',
                                       callback_group=self.group)
        self.arm_owner = ArmActionOwner(self.trajectory)
        self.tracking = TrackingSupport(self)
        self.create_service(Trigger, '~/stow', self.stow, callback_group=self.group)
        self.action = ActionServer(
            self, PickObject, '~/pick_object', execute_callback=self.execute,
            goal_callback=self.accept_goal, cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=self.group)

    def on_joints(self, message):
        with self.lock:
            self.arm = joint_snapshot(message.name, message.position, ARM_NAMES)
            self.received = time.monotonic()
            self.stamp = seconds(message.header.stamp)
            self.tracking.on_joints(message)

    def measured_safe(self):
        ros_age = self.get_clock().now().nanoseconds * 1e-9 - self.stamp
        return (safe_arm(self.arm, time.monotonic() - self.received)
                and self.stamp > 0 and -0.05 <= ros_age <= 0.5)

    def on_configure(self, state):
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state):
        with self.lock:
            self.enabled = True
            self.safe = False
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state):
        with self.lock:
            self.enabled = self.safe = False
            self.tracking.disable('lifecycle inactive')
            self.arm_owner.cancel(now=time.monotonic())
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state):
        return self.on_deactivate(state)

    def on_shutdown(self, state):
        return self.on_deactivate(state)

    def begin_shutdown(self):
        # Keep context/executor and the physical controller alive for cancel/result.
        self.on_deactivate(None)

    def shutdown_ready(self):
        return self.arm_owner.pending is None

    def destroy_node(self):
        # The executor's existing ownership drain remains authoritative. Emit
        # diagnostics while the node/context logger is still alive, not later
        # from Context.on_shutdown after ROS has already invalidated rosout.
        if hasattr(self, 'tracking'):
            self.tracking.trace.close()
        return super().destroy_node()

    def stow(self, request, response):
        with self.lock:
            if not self.enabled or self.busy or not self.tracking.guard.arm_available:
                response.message = 'Arm inactive or busy'
                return response
            self.busy = True
            self.work_running = True
            self.safe = False
        record = None
        try:
            if not self.trajectory.wait_for_server(timeout_sec=5):
                raise TimeoutError('arm trajectory controller unavailable')
            goal = FollowJointTrajectory.Goal()
            goal.trajectory.joint_names = list(ARM_NAMES)
            point = JointTrajectoryPoint(positions=list(SAFE_ARM))
            point.time_from_start.sec = 2
            goal.trajectory.points = [point]
            with self.lock:
                if not self.enabled:
                    raise RuntimeError('lifecycle became inactive')
                record = self.arm_owner.send(goal, now=time.monotonic(), timeout=8.)
            deadline = time.monotonic()+8.
            while self.enabled and not record.terminal and time.monotonic() < deadline:
                time.sleep(.01)
            if not record.terminal or record.result is None:
                raise RuntimeError(record.error or 'safe pose trajectory did not complete')
            result = record.result
            if (result.status != GoalStatus.STATUS_SUCCEEDED
                    or result.result.error_code != FollowJointTrajectory.Result.SUCCESSFUL):
                raise RuntimeError('safe pose trajectory failed')
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                with self.lock:
                    if self.enabled and self.measured_safe():
                        self.safe = True
                        response.success = True
                        response.message = 'Safe upright zero pose measured; not a folded carry pose'
                        return response
                time.sleep(0.02)
            raise TimeoutError('fresh measured safe arm pose unavailable')
        except Exception as exc:
            if record is not None and not record.terminal:
                self.arm_owner.cancel(now=time.monotonic())
            response.message = str(exc)
        finally:
            with self.lock:
                self.work_running = False
                self.busy = self.arm_owner.pending is not None or bool(self.arm_owner.fault)
        return response

    def accept_goal(self, goal):
        pose = goal.target_pose.pose
        now = self.get_clock().now().nanoseconds * 1e-9
        stamp = seconds(goal.target_pose.header.stamp)
        error = validate_target(
            goal.object_name, goal.target_pose.header.frame_id,
            stamp, now,
            [pose.position.x, pose.position.y, pose.position.z],
            [pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w],
            goal.dry_run)
        with self.lock:
            if (error or not self.enabled or not self.safe or self.busy or not self.measured_safe()
                    or not self.tracking.guard.arm_available):
                self.get_logger().info(
                    f'Pick rejected: {error or "inactive, unsafe, or busy"}; age_s={now-stamp:.6f}')
                return GoalResponse.REJECT
            self.busy = True
            self.work_running = True
        return GoalResponse.ACCEPT

    def execute(self, handle):
        result = PickObject.Result(success=False)
        try:
            # Protocol rehearsal intentionally sends no grasp/motion commands.
            # distance_remaining is unknown without a planner, represented by NaN.
            for stage in ('Validating', 'PlanningUnavailable', 'DryRunReview'):
                handle.publish_feedback(PickObject.Feedback(
                    current_state=stage, distance_remaining=math.nan))
                deadline = time.monotonic() + 0.6
                while time.monotonic() < deadline:
                    if handle.is_cancel_requested:
                        handle.canceled()
                        result.error_code = PickObject.Result.CANCELED
                        result.message = 'Dry-run canceled; no physical grasp performed'
                        return result
                    with self.lock:
                        if not self.enabled or not self.measured_safe():
                            handle.abort()
                            result.error_code = PickObject.Result.NOT_READY
                            result.message = 'Lifecycle or fresh arm safety gate lost'
                            return result
                    time.sleep(0.02)
            handle.abort()
            result.error_code = PickObject.Result.NOT_IMPLEMENTED
            result.message = 'Protocol rehearsal complete; MoveIt and physical grasp not implemented'
            return result
        finally:
            with self.lock:
                self.busy = False
                self.work_running = False


def main():
    spin(ManipulationNode)
