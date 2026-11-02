"""Original simulation cadence and an independent wall watchdog over real DDS.

No clock values are replaced. Controlled clocks/feedback are test inputs only,
never native acceptance. Catches a wall timer reusing one simulation instant.
"""
import json,time
import pytest
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock
from builtin_interfaces.msg import Time
from lifecycle_msgs.msg import Transition
from integrated_robot_navigation.crawl_controller import CrawlController
from integrated_robot_navigation.clock_execution import make_control_executor
from test_execution_admission_contract import fixture
from test_crawl_lifecycle import CrawlRig


def controller(context,model,profile,expected,*,g2=True,engine='mujoco'):
    expected={**expected,'control_clock':'relay100'}
    return CrawlController(model,profile,engine,context=context,
        cli_args=['--ros-args','-r','/clock:=/navigation/control_clock'],parameter_overrides=[
            Parameter('use_sim_time',value=True),Parameter('validation_mode',value=True),
            Parameter('g2_validation_mode',value=g2),Parameter('control_clock_mode',value='relay100'),
            Parameter('native_execution_profile',value=json.dumps(expected) if g2 else '')])


@pytest.mark.parametrize('g2',[False,True])
def test_mujoco_model_owner_dispatch_is_serial_after_ingress_is_isolated(tmp_path,nav_robot_model,g2):
    from rclpy.executors import SingleThreadedExecutor
    profile,expected=fixture(tmp_path,nav_robot_model,'mujoco')
    ctx=Context();rclpy.init(context=ctx);node=controller(ctx,nav_robot_model,profile,expected,g2=g2)
    executor=make_control_executor(node)
    try:
        assert isinstance(executor,SingleThreadedExecutor), 'single model owner still incurs an unnecessary callback worker queue'
        assert node.ingress_worker.snapshot()['alive'] and not node.active
        assert node.command_publication_count==0
        if not g2:
            assert not node.simulation_cadence and node.reference_dispatch is None
            assert node.applied_credit is None
            assert node.ingress_worker.snapshot()['dispatch']=='owned_serial_waitset'
    finally:
        assert executor.shutdown(timeout_sec=2.)
        node.destroy_node();ctx.try_shutdown()


def test_g2_control_waits_for_original_simulation_progress_but_wall_watchdog_still_runs(tmp_path,nav_robot_model,monkeypatch):
    ctx=Context();rclpy.init(context=ctx);calls=[]
    def record(node):calls.append((node.get_clock().now().nanoseconds,time.monotonic_ns()))
    monkeypatch.setattr(CrawlController,'_tick',record)  # instrument dispatch only; no motor/model fixture
    profile,expected=fixture(tmp_path,nav_robot_model,'mujoco')
    node=controller(ctx,nav_robot_model,profile,expected)
    peer=Node('g2_cadence_source',context=ctx);executor=make_control_executor(node)
    executor.add_node(node);executor.add_node(peer)
    pub=peer.create_publisher(Clock,'/navigation/control_clock',10)
    def pump(seconds,stamp=None):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if stamp is not None:pub.publish(Clock(clock=Time(sec=stamp//10**9,nanosec=stamp%10**9)))
            executor.spin_once(timeout_sec=.001)
            time.sleep(.001)
    try:
        pump(.15,1_000_000_000);pump(.035,1_100_000_000)
        assert calls and node.get_clock().now().nanoseconds==1_100_000_000
        calls.clear();pump(.10)
        assert not calls, 'wall control timer consumed the same simulation instant repeatedly'
        for index in range(1,23):pump(.01,1_100_000_000+index*10_000_000)
        progressed=list(calls)
        assert len(progressed)>=7
        assert all(b[0]>a[0] for a,b in zip(progressed,progressed[1:])), 'control dispatched without ROS progress'
        calls.clear();pause=time.monotonic_ns();pump(.26)
        assert calls, 'paused simulation also stopped the independent wall watchdog'
        assert calls[0][1]-pause>=150_000_000
        assert all(stamp==1_320_000_000 for stamp,_ in calls)
        assert node.command_publication_count==0
    finally:
        assert executor.shutdown(timeout_sec=2.)
        node.destroy_node();peer.destroy_node();ctx.try_shutdown()


def test_g2_paused_clock_faults_and_never_resumes_commands_on_later_transport(tmp_path,nav_robot_model):
    profile,expected=fixture(tmp_path,nav_robot_model,'mujoco')
    ctx=Context();rclpy.init(context=ctx);node=controller(ctx,nav_robot_model,profile,expected)
    rig=CrawlRig(node,nav_robot_model,ctx)
    rig.node.destroy_publisher(rig.clock)
    rig.clock=rig.node.create_publisher(Clock,'/navigation/control_clock',10)
    try:
        rig.pump(.3)
        assert rig.transition(Transition.TRANSITION_CONFIGURE)
        assert rig.transition(Transition.TRANSITION_ACTIVATE)
        rig.pump(.1);assert rig.commands
        rig.pump(.3,clock=False)
        assert rig.crawl_states[-1].state=='FAULT'
        assert not rig.crawl_states[-1].stopped
        count=len(rig.commands);rig.pump(.2,clock=True)
        assert rig.crawl_states[-1].state=='FAULT' and len(rig.commands)==count
    finally:
        rig.close();ctx.try_shutdown()


@pytest.mark.parametrize('g2',[False,True])
@pytest.mark.parametrize('engine',['mujoco','gazebo'])
def test_actual_owner_records_bounded_ordered_decision_costs_without_changing_clock(tmp_path,nav_robot_model,g2,engine):
    if engine=='gazebo' and g2:
        from test_stance_load_transfer import helper
        nav_robot_model=helper(nav_robot_model).model
    profile,expected=fixture(tmp_path,nav_robot_model,engine)
    ctx=Context();rclpy.init(context=ctx);node=controller(ctx,nav_robot_model,profile,expected,g2=g2,engine=engine)
    rig=CrawlRig(node,nav_robot_model,ctx)
    rig.node.destroy_publisher(rig.clock)
    rig.clock=rig.node.create_publisher(Clock,'/navigation/control_clock',10)
    try:
        rig.pump(.3)
        assert rig.transition(Transition.TRANSITION_CONFIGURE)
        # This fixture publishes on the model executor's parent thread.
        # Native numeric prepare can block it during configure. Refresh actual
        # synthetic captures before the FIRST activation; keep all age checks.
        # Real engine/guard producers run in independent processes.
        rig.pump(.1)
        assert node.machine.load_result_timing==('same_cycle' if engine=='gazebo' and g2 else 'strict')
        expected_receipt='event_receiver' if engine=='gazebo' and g2 else 'model_poll'
        assert node.machine.load_receipt_mode==expected_receipt
        if node.machine._load_transfer is not None and node.machine._load_transfer.asynchronous:
            assert node.machine._load_transfer.snapshot()['receipt_mode']==expected_receipt
        assert rig.transition(Transition.TRANSITION_ACTIVATE)
        rig.pump(.1)
        rows=getattr(node,'decision_cost_trace',None)
        assert rows, 'actual owner decision boundaries are not observable'
        assert rows.maxlen==512
        complete=[row for row in rows if 'model' in [stage[0] for stage in row['stages']]]
        assert complete
        names=('clock','bundle','command','leg_owner','guard','command_gate',
            'native_credit','reference_rate','model_validate','model_fk','model_mass',
            'model_safety','model_solve','model','publication','status')
        for row in complete:
            assert tuple(stage[0] for stage in row['stages'])==names
            times=[row['started_wall_ns'],*[stage[1] for stage in row['stages']],row['finished_wall_ns']]
            assert times==sorted(times)
            assert all(len(stage)==3 for stage in row['stages']), 'owner CPU time cannot be separated from preemption'
            cpu=[row['started_thread_ns'],*[stage[2] for stage in row['stages']],row['finished_thread_ns']]
            assert cpu==sorted(cpu) and row['native_tid']>0
            assert row['decision_ros_ns']<=node.get_clock().now().nanoseconds
        assert node.machine.state=='STAND' and rig.commands
        if g2 and engine=='mujoco':assert not node.applied_credit.pending
        else:assert node.applied_credit is None and not node.simulation_cadence
    finally:
        rig.close();ctx.try_shutdown()
