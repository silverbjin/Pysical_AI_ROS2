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

from .common import seconds, spin, wait_future
from .policy import ARM_NAMES, SAFE_ARM, joint_snapshot, safe_arm, validate_target


class ManipulationNode(LifecycleNode):
    def __init__(self):
        super().__init__('manipulation_node')
        self.lock = threading.RLock()
        self.enabled = False
        self.busy = False
        self.safe = False
        self.arm = None
        self.received = self.stamp = 0.0
        self.group = ReentrantCallbackGroup()
        self.create_subscription(JointState, '/joint_states', self.on_joints, 10,
                                 callback_group=self.group)
        self.trajectory = ActionClient(self, FollowJointTrajectory,
                                       '/arm_trajectory_controller/follow_joint_trajectory',
                                       callback_group=self.group)
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
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state):
        return self.on_deactivate(state)

    def on_shutdown(self, state):
        return self.on_deactivate(state)

    def stow(self, request, response):
        with self.lock:
            if not self.enabled or self.busy:
                response.message = 'Arm inactive or busy'
                return response
            self.busy = True
            self.safe = False
        handle = None
        try:
            if not self.trajectory.wait_for_server(timeout_sec=5):
                raise TimeoutError('arm trajectory controller unavailable')
            goal = FollowJointTrajectory.Goal()
            goal.trajectory.joint_names = list(ARM_NAMES)
            point = JointTrajectoryPoint(positions=list(SAFE_ARM))
            point.time_from_start.sec = 2
            goal.trajectory.points = [point]
            handle = wait_future(self.trajectory.send_goal_async(goal), 5,
                                 lambda: self.enabled)
            if not handle.accepted:
                raise RuntimeError('safe pose trajectory rejected')
            result = wait_future(handle.get_result_async(), 8, lambda: self.enabled)
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
            if handle is not None and handle.accepted:
                handle.cancel_goal_async()
            response.message = str(exc)
        finally:
            with self.lock:
                self.busy = False
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
            if error or not self.enabled or not self.safe or self.busy or not self.measured_safe():
                self.get_logger().info(
                    f'Pick rejected: {error or "inactive, unsafe, or busy"}; age_s={now-stamp:.6f}')
                return GoalResponse.REJECT
            self.busy = True
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


def main():
    spin(ManipulationNode)
