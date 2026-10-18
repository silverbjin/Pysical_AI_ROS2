#!/usr/bin/env python3
"""Exercise real ROS APIs against a running engine and architecture launch."""
import argparse
import json
import statistics
import time
from pathlib import Path

import rclpy
from action_msgs.msg import GoalStatus
from integrated_robot_interfaces.action import PickObject
from integrated_robot_interfaces.srv import SetMode
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState, GetState
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Float64MultiArray, String
from std_srvs.srv import Trigger


class Probe(Node):
    def __init__(self):
        super().__init__('architecture_probe', parameter_overrides=[
            Parameter('use_sim_time', value=True)])
        self.startup = None
        self.commands = []
        self.sync = []
        self.feedback = []
        self.loc = None
        self.bad_sensor = False
        self.create_subscription(String, '/architecture/startup', self.on_startup,
                                 QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(Float64MultiArray, '/leg_position_controller/commands',
                                 lambda msg: self.commands.append(time.monotonic()), 100)
        self.create_subscription(String, '/architecture/synchronized',
                                 lambda msg: self.sync.append(json.loads(msg.data)), 20)
        self.create_subscription(String, '/architecture/locomotion', self.on_loc, 10)
        self.images = self.create_publisher(Image, '/architecture/image_raw', qos_profile_sensor_data)
        self.odoms = self.create_publisher(Odometry, '/architecture/odom', qos_profile_sensor_data)
        self.create_timer(0.05, self.sensors)
        self.pick = ActionClient(self, PickObject, '/manipulation_node/pick_object')

    def on_startup(self, msg):
        self.startup = json.loads(msg.data)

    def on_loc(self, msg):
        self.loc = json.loads(msg.data)

    def sensors(self):
        image, odom = Image(), Odometry()
        stamp = self.get_clock().now().to_msg()
        if self.bad_sensor:
            stamp.sec -= 2
        image.header.stamp = stamp
        odom.header.stamp = stamp
        image.header.frame_id = 'camera_link'
        odom.header.frame_id = 'odom'
        image.height = image.width = 1
        image.encoding = 'mono8'
        image.step = 1
        image.data = [0]
        odom.pose.pose.orientation.w = 1.0
        self.images.publish(image)
        self.odoms.publish(odom)

    def until(self, predicate, timeout=20):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.02)
            if predicate():
                return
        raise TimeoutError('architecture verification deadline exceeded')

    def pump(self, duration):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.02)

    def call(self, kind, path, request):
        client = self.create_client(kind, path)
        try:
            assert client.wait_for_service(timeout_sec=10), path
            future = client.call_async(request)
            self.until(future.done)
            return future.result()
        finally:
            self.destroy_client(client)

    def goal(self, dry_run=True, stale=False):
        goal = PickObject.Goal()
        goal.object_name = 'cup'
        goal.dry_run = dry_run
        goal.target_pose.header.frame_id = 'base_link'
        goal.target_pose.header.stamp = self.get_clock().now().to_msg()
        if stale:
            goal.target_pose.header.stamp.sec -= 5
        goal.target_pose.pose.position.x = 0.3
        goal.target_pose.pose.position.z = 0.4
        goal.target_pose.pose.orientation.w = 1.0
        future = self.pick.send_goal_async(
            goal, feedback_callback=lambda msg: self.feedback.append(msg.feedback.current_state))
        self.until(future.done)
        return future.result()

    def run(self):
        self.until(lambda: self.startup is not None, 60)
        assert self.startup['status'] == 'READY', self.startup
        assert self.startup['events'] == [
            'arm_configured', 'legs_configured', 'arm_active', 'arm_safe', 'legs_active']
        self.until(lambda: len(self.sync) >= 3 and len(self.commands) >= 100)
        assert all(abs(item['skew_s']) <= 0.05 for item in self.sync)
        assert self.pick.wait_for_server(timeout_sec=10)
        assert not self.goal(dry_run=False).accepted
        assert not self.goal(stale=True).accepted
        handle = self.goal()
        assert handle.accepted
        assert not self.goal().accepted, 'second overlapping goal must be rejected'
        self.until(lambda: bool(self.feedback))
        cancel = handle.cancel_goal_async()
        self.until(cancel.done)
        canceled = handle.get_result_async()
        self.until(canceled.done)
        assert canceled.result().status == GoalStatus.STATUS_CANCELED
        assert not canceled.result().result.success
        handle = self.goal()
        assert handle.accepted
        done = handle.get_result_async()
        self.until(done.done)
        assert done.result().status == GoalStatus.STATUS_ABORTED
        assert done.result().result.error_code == PickObject.Result.NOT_IMPLEMENTED
        assert not done.result().result.success
        mission = self.call(Trigger, '/mission_commander/rehearse_pick', Trigger.Request())
        assert not mission.success
        assert 'not implemented' in mission.message
        mode = self.call(SetMode, '/locomotion_node/set_mode', SetMode.Request(mode='WALK'))
        assert not mode.accepted
        self.pump(3)
        periods = [b-a for a, b in zip(self.commands, self.commands[1:])]
        assert len(periods) >= 100
        # This is a measured lab tolerance, not a hard realtime guarantee.
        assert statistics.median(periods) < 0.04, statistics.median(periods)
        self.bad_sensor = True
        self.pump(1)
        before = len(self.sync)
        self.pump(1)
        assert len(self.sync) == before, 'stale synchronized pairs must not be processed'
        stopped = self.call(SetMode, '/locomotion_node/set_mode', SetMode.Request(mode='STOP'))
        assert stopped.accepted
        self.pump(0.2)
        before = len(self.commands)
        self.pump(0.4)
        assert len(self.commands) == before
        request = ChangeState.Request()
        request.transition.id = Transition.TRANSITION_DEACTIVATE
        assert self.call(ChangeState, '/locomotion_node/change_state', request).success
        assert not self.call(SetMode, '/locomotion_node/set_mode',
                             SetMode.Request(mode='STAND')).accepted
        self.pump(0.3)
        assert len(self.commands) == before
        return {
            'status': 'PASS', 'startup': self.startup, 'command_samples': len(periods),
            'median_period_s': statistics.median(periods),
            'p95_period_s': sorted(periods)[int(len(periods)*0.95)],
            'max_period_s': max(periods), 'synchronized_samples': len(self.sync),
            'feedback': sorted(set(self.feedback)), 'cancel': 'PASS',
            'overlapping_goal_rejection': 'PASS', 'unimplemented_grasp_is_failure': 'PASS',
            'stale_pair_rejection': 'PASS', 'inactive_output_gate': 'PASS',
            'mission_preserves_task_failure': 'PASS',
        }

    def startup_failure(self):
        self.until(lambda: self.startup is not None, 40)
        assert self.startup['status'] == 'FAILED', self.startup
        assert 'legs_active' not in self.startup['events']
        state = self.call(GetState, '/manipulation_node/get_state', GetState.Request())
        assert state.current_state.label == 'inactive'
        legs = self.call(GetState, '/locomotion_node/get_state', GetState.Request())
        assert legs.current_state.label == 'inactive'
        self.pump(1)
        assert not self.commands
        return {'status': 'PASS', 'startup': self.startup,
                'arm_rolled_back_to_inactive': True, 'leg_commands': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--expect-startup-failure', action='store_true')
    args = parser.parse_args()
    rclpy.init()
    probe = Probe()
    result = {'status': 'FAIL'}
    try:
        result = probe.startup_failure() if args.expect_startup_failure else probe.run()
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        probe.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
