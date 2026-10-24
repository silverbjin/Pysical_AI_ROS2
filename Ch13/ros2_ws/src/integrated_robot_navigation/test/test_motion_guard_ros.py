"""Actual DDS/time/watchdog tests; native evidence admission alone is stubbed.

No engine or gait runs here. The unstubbed offline profile rejection is tested
separately, so passing a transport test is never reported as G1 authorization.
"""
import importlib
import time

import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist, Point
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState, Imu, LaserScan
from rosgraph_msgs.msg import Clock
from builtin_interfaces.msg import Time
from integrated_robot_interfaces.msg import FootContacts, MotionState
from integrated_robot_interfaces.srv import SetMode
from integrated_robot_navigation.carry_profile import prepare_profile
from guard_fixture import bundle, CARRY


class Rig:
    def __init__(self, guard, model, context, *, executor_factory=None):
        self.guard = guard
        self.model = model
        self.node = Node('guard_test_producer', context=context)
        from integrated_robot_navigation.dispatch_node import make_navigation_executor
        self.executor = (executor_factory or make_navigation_executor)(guard)
        self.executor.add_node(self.node)
        self.executor.add_node(guard)
        self.start = time.monotonic()
        self.capture = 4.
        self.generation = 0
        self.ready = True
        self.outputs, self.states = [], []
        qos = qos_profile_sensor_data
        self.pubs = {key: self.node.create_publisher(kind, topic, qos if key not in ('raw', 'smoothed', 'legs') else 10)
                     for key, kind, topic in (
            ('raw', Twist, '/navigation/cmd_vel_raw'), ('smoothed', Twist, '/navigation/cmd_vel_smoothed'),
            ('joints', JointState, '/joint_states'), ('imu', Imu, '/navigation/imu'),
            ('contacts', FootContacts, '/navigation/foot_contacts'), ('body', Odometry, '/odom'),
            ('scan', LaserScan, '/scan'), ('carry', MotionState, '/navigation/carry_state'))}
        from std_msgs.msg import Float64MultiArray
        self.leg = self.node.create_publisher(Float64MultiArray, '/leg_position_controller/commands', 10)
        self.clock = self.node.create_publisher(Clock, '/clock', 10)
        self.output_sub = self.node.create_subscription(Twist, '/navigation/cmd_vel',
            lambda msg: self.outputs.append((time.monotonic(), msg.linear.x, msg.angular.z)), 10)
        self.state_sub = self.node.create_subscription(MotionState, '/navigation/guard_state',
            lambda msg: self.states.append(msg), 10)
        self.client = self.node.create_client(SetMode, '/navigation/set_mode')

    def pump(self, duration, *, raw=True, clock=True, scan=True):
        end = time.monotonic()+duration
        while time.monotonic() < end:
            if clock:
                self.capture = 4.+time.monotonic()-self.start
            sec = int(self.capture)
            stamp = Time(sec=sec, nanosec=int((self.capture-sec)*1e9))
            if clock:
                self.clock.publish(Clock(clock=stamp))
            state = bundle(self.model)
            for key in ('joints', 'imu', 'contacts', 'body', 'scan', 'carry'):
                if key == 'scan' and not scan:
                    continue
                if key == 'joints':
                    data = state.joints.data
                    msg = JointState(name=list(data['position']), position=list(data['position'].values()),
                                     velocity=list(data['velocity'].values()))
                elif key == 'imu':
                    msg = Imu()
                    msg.linear_acceleration.z = 9.81
                elif key == 'contacts':
                    data = state.contacts.data
                    msg = FootContacts(names=list(data['names']), normal_forces=list(data['forces']),
                        touching=list(data['touching']), sequence=int(self.capture*1e9),
                        points=[Point(x=p[0], y=p[1], z=p[2]) for p in data['points']])
                elif key == 'body':
                    msg = Odometry(child_frame_id='base_footprint')
                    msg.pose.pose.position.z = .46
                    msg.pose.pose.orientation.w = 1.
                elif key == 'scan':
                    msg = LaserScan(angle_min=-3.141592653589793,
                        angle_increment=6.283185307179586/360, range_min=.05, range_max=10.,
                        ranges=[float('inf')]*360)
                else:
                    msg = MotionState(ready=self.ready, generation=self.generation,
                                      model_sha256=self.model.model_sha256)
                msg.header.stamp = stamp
                msg.header.frame_id = getattr(state, key).frame_id
                self.pubs[key].publish(msg)
            command = Twist()
            command.linear.x, command.angular.z = .006, .01
            if raw:
                self.pubs['raw'].publish(command)
            self.pubs['smoothed'].publish(command)
            for _ in range(24):
                self.executor.spin_once(timeout_sec=.0005)
            time.sleep(.005)

    def mode(self, name):
        assert self.client.wait_for_service(timeout_sec=1.)
        future = self.client.call_async(SetMode.Request(mode=name))
        deadline = time.monotonic()+2.
        while not future.done() and time.monotonic() < deadline:
            self.pump(.02)
        assert future.done(), 'mode service deadline'
        return future.result()

    def close(self):
        self.executor.shutdown(timeout_sec=2.)
        if self.guard is not None:
            self.guard.destroy_node()
        self.node.destroy_node()


@pytest.fixture
def rig(nav_robot_model, monkeypatch):
    module = importlib.import_module('integrated_robot_navigation.motion_guard')
    assert hasattr(module, 'MotionGuardNode'), 'steady watchdog ROS wrapper missing'
    profile = prepare_profile(nav_robot_model, CARRY)
    monkeypatch.setattr(module, 'validate_profile', lambda *args: (True, 'unit_admission_stub'))
    ctx = Context()
    rclpy.init(context=ctx)
    guard = module.MotionGuardNode(nav_robot_model, profile, 'mujoco', context=ctx,
        parameter_overrides=[Parameter('use_sim_time', value=True)])
    value = Rig(guard, nav_robot_model, ctx)
    try:
        value.pump(.5)
        yield value
    finally:
        value.close()
        ctx.try_shutdown()


def test_raw_loss_zeros_while_ros_clock_paused_and_smoother_continues(rig):
    assert rig.mode('CRAWL').accepted
    rig.pump(.15)
    assert any(x > 0. for _, x, _ in rig.outputs)
    rig.pump(.14, raw=False)
    rig.pump(.14, raw=False, clock=False)
    assert rig.outputs[-1][1:] == (0., 0.)
    assert rig.states[-1].fault_reason == 'raw:wall_age'
    rig.pump(.1)
    assert rig.outputs[-1][1:] == (0., 0.)
    assert not rig.mode('CRAWL').accepted


def test_offline_profile_is_rejected_by_real_ros_activation_service(rig, monkeypatch):
    from integrated_robot_navigation.carry_profile import validate_profile
    module = importlib.import_module('integrated_robot_navigation.motion_guard')
    monkeypatch.setattr(module, 'validate_profile', validate_profile)
    response = rig.mode('CRAWL')
    assert not response.accepted and response.message == 'native_validation_required'
    assert all(x == 0. and w == 0. for _, x, w in rig.outputs)


def test_shutdown_joins_watchdog_and_publishes_final_not_ready_zero(rig):
    assert rig.mode('CRAWL').accepted
    rig.pump(.1)
    old = rig.guard
    rig.executor.remove_node(old)
    old.destroy_node()
    rig.guard = None
    for _ in range(30):
        rig.executor.spin_once(timeout_sec=.002)
    assert rig.outputs[-1][1:] == (0., 0.)
    assert not rig.states[-1].ready


@pytest.mark.parametrize('fault', ['producer', 'owner_replaced', 'carry', 'scan', 'generation'])
def test_real_dds_faults_require_reset_not_just_recovered_inputs(rig, fault):
    assert rig.mode('CRAWL').accepted
    rig.pump(.1)
    if fault == 'producer':
        extra = rig.node.create_publisher(Twist, '/navigation/cmd_vel_raw', 10)
        rig.pump(.35)
        rig.node.destroy_publisher(extra)
    elif fault == 'owner_replaced':
        # Count returns to one before spinning; endpoint identity must still
        # require re-arming instead of silently adopting the replacement.
        rig.node.destroy_publisher(rig.pubs['raw'])
        rig.pubs['raw'] = rig.node.create_publisher(Twist, '/navigation/cmd_vel_raw', 10)
        rig.pump(.15)
    elif fault == 'carry':
        rig.ready = False
        rig.pump(.1)
        rig.ready = True
    elif fault == 'scan':
        rig.pump(.4, scan=False)
    else:
        assert rig.mode('RESET').accepted
        # Old carry generation continues over actual DDS after the reset.
        assert rig.mode('CRAWL').accepted
        rig.pump(.1)
    assert rig.outputs[-1][1:] == (0., 0.)
    assert rig.states[-1].fault_reason
    rig.pump(.1)
    assert rig.outputs[-1][1:] == (0., 0.)
