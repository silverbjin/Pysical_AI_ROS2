"""Real action wire/terminal/receipt tests; the peer is not a physics engine."""
from dataclasses import replace
from collections import deque
import importlib
import json
import os
from pathlib import Path
import threading
import time
import uuid

import pytest
import rclpy
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.context import Context
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, Header
from std_srvs.srv import Trigger
from control_msgs.action import FollowJointTrajectory
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_navigation.carry_profile import prepare_profile
from guard_fixture import CARRY, bundle
from carry_feedback_peer import CarryFeedbackPeer


class CarryRig:
    def __init__(self, model, manager_type):
        # Acquire the independent peer before any parent ROS/action resources.
        # A failed child startup must not leak an already-running action receiver.
        self.feedback = CarryFeedbackPeer(model.model_sha256, bundle(model).joints.data['position'])
        self.ctx = Context()
        rclpy.init(context=self.ctx)
        parameters = [Parameter('use_sim_time', value=True)]
        self.peer = Node('carry_real_action_peer', context=self.ctx, parameter_overrides=parameters)
        self.manager = manager_type(model, prepare_profile(model, CARRY), context=self.ctx,
                                    parameter_overrides=parameters)
        self.model = model
        self.generation, self.stand = 0, True
        self.velocity, self.error = 0., 0.
        self.gripper_error, self.gripper_velocity = 0., 0.
        self.accept, self.release, self.executed = (threading.Event() for _ in range(3))
        self.accept.set()
        self.server = ActionServer(self.peer, FollowJointTrajectory,
            '/arm_trajectory_controller/follow_joint_trajectory', self.execute,
            goal_callback=self.goal, cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=ReentrantCallbackGroup())
        self.states, self.gripper_commands = [], []
        self.publish_times = deque(maxlen=256)
        self.publish_spans = []  # retain the first failure, not only the tail after it
        self.first_fault = None
        self.peer.create_subscription(MotionState, '/navigation/carry_state', self.receive_state, 10)
        self.peer.create_subscription(Float64MultiArray, '/gripper_position_controller/commands',
                                      self.gripper_commands.append, 10)
        self.prepare = self.peer.create_client(Trigger, '/carry_manager/prepare')
        self.stop = self.peer.create_client(Trigger, '/carry_manager/stop')
        # Production carry main uses a short SingleThreadedExecutor. The test
        # server may block acceptance/result deliberately, so it gets a separate
        # executor rather than changing the parent's production dispatch model.
        self.executor = MultiThreadedExecutor(num_threads=3, context=self.ctx)
        self.executor.add_node(self.peer)
        self.parent_executor = SingleThreadedExecutor(context=self.ctx)
        self.parent_executor.add_node(self.manager)
        self.running = True
        self.threads = [threading.Thread(target=self.spin, args=(executor,))
                        for executor in (self.executor, self.parent_executor)]
        for thread in self.threads:
            thread.start()

    def goal(self, goal):
        assert self.accept.wait(4.), 'test acceptance was never released'
        return GoalResponse.ACCEPT

    def receive_state(self, msg):
        self.states.append(msg)
        if msg.fault_reason and self.first_fault is None:
            with self.manager.lock:
                self.first_fault = dict(wall_ns=time.monotonic_ns(),
                    ros_ns=self.peer.get_clock().now().nanoseconds,
                    diagnostics=list(self.manager.diagnostics),
                    selected={key: dict(stamp_ns=value.stamp_ns, received_ns=value.received_ns,
                                        data=value.data) if value else None
                              for key, value in self.manager.selected.items()})

    def execute(self, handle):
        self.executed.set()
        assert self.release.wait(4.), 'test terminal was never released'
        if handle.is_cancel_requested:
            handle.canceled()
        else:
            handle.succeed()
        return FollowJointTrajectory.Result(error_code=0)

    def spin(self, executor):
        while self.running:
            executor.spin_once(timeout_sec=.01)

    def pump(self, duration):
        end = time.monotonic()+duration
        while time.monotonic() < end:
            self.publish_times.append(time.monotonic_ns())
            self.feedback.update(self.generation, self.stand, self.velocity, self.error,
                                 self.gripper_error, self.gripper_velocity)
            time.sleep(.01)

    def call(self, client):
        assert client.wait_for_service(timeout_sec=2.)
        future = client.call_async(Trigger.Request())
        deadline = time.monotonic()+2.
        while not future.done() and time.monotonic() < deadline:
            self.pump(.02)
        assert future.done(), 'short service blocked on action completion'
        return future.result()

    def wait_for(self, condition, description, timeout=1.):
        # Await the actual asynchronous observation, not an assumed .1s DDS
        # delivery. Input capture/receipt watchdogs still run unchanged and any
        # unexpected sticky fault fails the caller's assertion, never retries.
        deadline = time.monotonic()+timeout
        while not condition() and time.monotonic() < deadline:
            self.pump(.01)
        assert condition(), dict(waiting_for=description, fault=self.manager.fault,
                                diagnostics=list(self.manager.diagnostics))

    def close(self):
        self.accept.set()
        self.manager.begin_shutdown()
        self.release.set()
        end = time.monotonic()+2.
        while not self.manager.shutdown_ready() and time.monotonic() < end:
            self.pump(.02)
        assert self.manager.shutdown_ready(), self.manager.owner.snapshot()
        self.running = False
        for thread in self.threads:
            thread.join(2.)
        self.executor.shutdown(timeout_sec=3.)
        self.parent_executor.shutdown(timeout_sec=3.)
        self.server.destroy()  # native action waitables are not Node-owned publishers
        self.manager.destroy_node()
        assert self.manager.transport.closed and not self.manager.transport.thread.is_alive()
        self.peer.destroy_node()
        self.ctx.try_shutdown()
        self.publish_spans = self.feedback.close()


@pytest.fixture
def carry_rig(nav_robot_model):
    module = importlib.import_module('integrated_robot_navigation.carry_manager') if importlib.util.find_spec(
        'integrated_robot_navigation.carry_manager') else None
    assert module is not None, 'measured carry owner missing'
    rig = CarryRig(nav_robot_model, module.CarryManager)
    try:
        rig.pump(.25)
        deadline = time.monotonic()+2.
        while time.monotonic() < deadline:
            try:
                rig.manager._owners()
                if rig.manager.transport.client.server_is_ready():
                    break
            except ValueError:
                pass
            rig.pump(.03)
        rig.manager._owners()
        yield rig
    finally:
        rig.close()
        target = os.environ.get('CH13_NAV_EVIDENCE')
        if target:
            with rig.manager.lock:
                trace = dict(publish_spans=list(rig.publish_spans), first_fault=rig.first_fault,
                    feedback_startup=rig.feedback.startup_trace,
                    feedback_pid=rig.feedback.process.pid, feedback_exitcode=rig.feedback.process.exitcode,
                    diagnostics=list(rig.manager.diagnostics), manager_fault=rig.manager.fault,
                    states=[dict(sec=m.header.stamp.sec, nsec=m.header.stamp.nanosec,
                                 state=m.state, generation=m.generation, fault=m.fault_reason)
                            for m in rig.states])
            with (Path(target)/('carry-wire-trace-'+str(uuid.uuid4())+'.json')).open('x') as handle:
                json.dump(trace, handle)


def test_stand_required_before_any_carry_goal(carry_rig):
    rig = carry_rig
    rig.stand = False
    rig.pump(.08)
    assert not rig.call(rig.prepare).success
    assert rig.manager.owner.pending is None and not rig.executed.is_set()


def test_peer_feedback_does_not_depend_on_test_assertion_thread(carry_rig):
    """The production sensor publisher is independent of its action client."""
    rig = carry_rig
    assert rig.call(rig.prepare).success
    time.sleep(.25)  # client is idle; the independent source must keep publishing
    assert not rig.manager.fault, rig.manager.fault
    assert rig.manager.owner.pending is not None


def test_actual_feedback_loss_still_cancels_and_retains_lease_until_result(carry_rig):
    rig = carry_rig
    assert rig.call(rig.prepare).success
    rig.feedback.enabled.clear()
    rig.wait_for(lambda: bool(rig.manager.fault), 'actual missing-input watchdog', timeout=.5)
    assert 'age' in rig.manager.fault
    # /clock paused with the source: the independent wall watchdog, not
    # progression of a fabricated ROS timestamp, must be what stops this lease.
    assert 'wall_age' in rig.manager.fault
    assert rig.manager.owner.pending is not None
    rig.feedback.enabled.set()
    rig.pump(.1)
    assert rig.manager.fault and not rig.states[-1].ready, 'fresh input cannot clear sticky failure'
    rig.release.set()
    rig.wait_for(lambda: rig.manager.owner.pending is None, 'received canceled result')


def test_delayed_acceptance_and_cancel_ack_never_release_without_result(carry_rig):
    rig = carry_rig
    rig.accept.clear()
    assert rig.call(rig.prepare).success
    rig.pump(.15)
    record = rig.manager.owner.pending
    assert record is not None and not record.terminal and not rig.states[-1].ready
    rig.accept.set()
    rig.pump(.15)
    assert rig.executed.is_set() and not record.terminal
    assert rig.call(rig.stop).success
    rig.pump(.12)
    assert any(row['event'] == 'cancel_ack' for row in rig.manager.owner.snapshot()['events'])
    assert rig.manager.owner.pending is record and not rig.states[-1].ready
    with pytest.raises(RuntimeError, match='terminal unconfirmed'):
        rig.manager.destroy_node()
    assert rig.manager.transport.healthy and rig.manager.owner.pending is record
    rig.release.set()
    rig.pump(.15)
    assert record.terminal and record.result.status == 5
    assert rig.manager.owner.pending is None and not rig.states[-1].ready


def test_terminal_success_then_actual_settle_for_one_second(carry_rig):
    rig = carry_rig
    assert rig.call(rig.prepare).success
    rig.pump(.12)
    assert rig.executed.is_set()
    rig.release.set()
    rig.pump(.65)
    assert rig.manager.record.terminal and not rig.states[-1].ready
    rig.pump(.6)
    assert rig.states[-1].ready and rig.gripper_commands, list(rig.manager.diagnostics)
    assert all(list(msg.data) == [.015, .015] for msg in rig.gripper_commands)
    rig.error = .04
    # A changed test-source setting, its actual DDS capture, controller fault,
    # and this client's status receipt are different asynchronous events.
    # Do not infer all four from an arbitrary 80ms client sleep. The production
    # input watchdog and the one-second measured settling rule are unchanged.
    rig.wait_for(lambda: bool(rig.manager.fault), 'measured carry posture fault', timeout=.5)
    assert rig.manager.fault == 'measured carry posture lost'
    with rig.manager.lock:
        selected = rig.manager.inbox.samples['joints']
        assert abs(selected.data['position']['arm_joint_2']-rig.manager.profile.arm_q[1]) == pytest.approx(.04)
    rig.wait_for(lambda: not rig.states[-1].ready
        and rig.states[-1].fault_reason == 'measured carry posture lost',
        'received measured posture fault status', timeout=.5)
    client = rig.peer.create_client(Trigger, '/carry_manager/report')
    first = json.loads(rig.call(client).message)['first_fault']
    assert first['reason'] == 'measured carry posture lost'
    assert first['state_before'] == 'READY'
    assert first['scope'] == 'selected_cache_at_first_failure'
    sample = first['selected_joint_sample']
    assert sample['stamp_ns'] > 0 and sample['received_ns'] > 0
    assert abs(sample['data']['position']['arm_joint_2']-rig.manager.profile.arm_q[1]) == pytest.approx(.04)
    rig.error = 0.
    rig.pump(1.1)
    assert not rig.states[-1].ready, 'fault must not automatically recover'
    assert json.loads(rig.call(client).message)['first_fault'] == first, 'later input must not overwrite first failure'


def test_actual_velocity_prevents_settle_even_after_terminal(carry_rig):
    rig = carry_rig
    rig.velocity = .021
    rig.pump(.04)
    assert rig.call(rig.prepare).success
    rig.release.set()
    rig.pump(1.15)
    assert rig.manager.record.terminal and not rig.states[-1].ready
    rig.velocity = 0.
    rig.pump(.7)
    assert not rig.states[-1].ready
    rig.pump(.5)
    assert rig.states[-1].ready, dict(diagnostics=list(rig.manager.diagnostics),
        max_publish_gap_ms=max(b-a for a, b in zip(rig.publish_times, list(rig.publish_times)[1:]))/1e6)


def test_actual_terminal_success_does_not_cover_stuck_arm(carry_rig):
    rig = carry_rig
    rig.error = .04
    rig.pump(.04)
    assert rig.call(rig.prepare).success
    rig.release.set()
    rig.pump(1.2)
    assert rig.manager.record.terminal and not rig.states[-1].ready
    assert not rig.states[-1].fault_reason
    rig.pump(10.)  # actual wall timeout, not a synthetic success or forged clock
    assert rig.states[-1].state == 'FAULT' and 'settle timeout' in rig.states[-1].fault_reason


@pytest.mark.parametrize('error,velocity', [(.003, 0.), (0., .006)])
def test_prismatic_gripper_does_not_use_arm_radian_tolerances(carry_rig, error, velocity):
    rig = carry_rig
    rig.gripper_error, rig.gripper_velocity = error, velocity
    rig.pump(.04)
    assert rig.call(rig.prepare).success
    rig.release.set()
    rig.pump(1.2)
    assert rig.manager.record.terminal
    assert not rig.states[-1].ready, '3mm error or 6mm/s is not the measured unloaded gripper hold'


def test_generation_change_cancels_without_adopting_foreign_lease(carry_rig):
    rig = carry_rig
    assert rig.call(rig.prepare).success
    rig.pump(.1)
    rig.generation = 1
    rig.wait_for(lambda: rig.states and bool(rig.states[-1].fault_reason), 'published generation fault')
    with rig.manager.lock:
        trace = dict(diagnostics=list(rig.manager.diagnostics),
                     selected={key: sample.data if sample else None
                               for key, sample in rig.manager.selected.items()},
                     pending={key: [(stamp, sample.data) for stamp, sample in rows.items()]
                              for key, rows in rig.manager.observed.items()},
                     manager_fault=rig.manager.fault,
                     states=[(msg.header.stamp.sec, msg.header.stamp.nanosec,
                              msg.generation, msg.state, msg.fault_reason) for msg in rig.states[-6:]])
    assert rig.states[-1].generation == 0 and rig.states[-1].fault_reason, trace
    assert rig.states[-1].fault_reason == 'carry generation changed', trace
    assert rig.manager.owner.pending is not None and not rig.states[-1].ready
    rig.release.set()
    rig.wait_for(lambda: rig.manager.owner.pending is None, 'received actual terminal result')
    assert rig.manager.owner.pending is None
    assert not rig.call(rig.prepare).success


def test_duplicate_gripper_owner_latches_fault(carry_rig):
    rig = carry_rig
    assert rig.call(rig.prepare).success
    other = rig.peer.create_publisher(Float64MultiArray, '/gripper_position_controller/commands', 10)
    rig.pump(.12)
    assert rig.states[-1].fault_reason and not rig.states[-1].ready
    rig.peer.destroy_publisher(other)
    rig.release.set()
    rig.pump(.12)
    assert not rig.call(rig.prepare).success


def test_foreign_real_action_cannot_become_this_carry_lease(carry_rig):
    rig = carry_rig
    foreign = ActionClient(rig.peer, FollowJointTrajectory,
                           '/arm_trajectory_controller/follow_joint_trajectory')
    try:
        assert foreign.wait_for_server(timeout_sec=2.)
        future = foreign.send_goal_async(FollowJointTrajectory.Goal())
        deadline = time.monotonic()+1.
        while not future.done() and time.monotonic() < deadline:
            rig.pump(.02)
        assert future.done() and future.result().accepted
        rig.pump(.1)
        assert rig.states[-1].fault_reason == 'foreign arm action owner'
        assert not rig.call(rig.prepare).success
        rig.release.set()
        result = future.result().get_result_async()
        deadline = time.monotonic()+1.
        while not result.done() and time.monotonic() < deadline:
            rig.pump(.02)
        assert result.done() and not rig.states[-1].ready
    finally:
        rig.release.set()
        foreign.destroy()


def test_profile_hash_mismatch_rejected_before_worker_starts(nav_robot_model):
    module = importlib.import_module('integrated_robot_navigation.carry_manager')
    ctx = Context()
    rclpy.init(context=ctx)
    before = set(threading.enumerate())
    try:
        with pytest.raises(ValueError, match='model'):
            module.CarryManager(nav_robot_model,
                replace(prepare_profile(nav_robot_model, CARRY), model_sha256='0'*64), context=ctx)
        assert set(threading.enumerate()) == before
    finally:
        ctx.try_shutdown()


def test_report_exposes_received_typed_result_not_only_status(carry_rig):
    rig = carry_rig
    assert rig.call(rig.prepare).success
    rig.release.set()
    rig.pump(.2)
    client = rig.peer.create_client(Trigger, '/carry_manager/report')
    result = json.loads(rig.call(client).message)
    assert result['terminal'] and result['result_future_done']
    assert result['result_status'] == 4 and result['result_error_code'] == 0
    assert result['pending_uuid'] is None and result['uuid']
    assert result['receiver_healthy']
