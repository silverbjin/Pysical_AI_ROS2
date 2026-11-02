"""Curve sampling within original elapsed time; native motor/ACK contract unchanged."""
from copy import deepcopy
from pathlib import Path
import json
import math
import numpy as np
import pytest
from integrated_robot_navigation.gait import CrawlMachine,blend
from integrated_robot_navigation.carry_profile import default_limits
from test_crawl_shift_clock_progress import shifting
from test_calibration_clock_progress import sample_at


def owner(model):
    return CrawlMachine(model,default_limits(),reference_time_policy='applied_shift_elapsed')


def test_shift_reference_does_not_catch_up_more_than_two_nominal_periods(nav_robot_model):
    case=json.loads((Path(__file__).parent/'fixtures/reference-095-carry.json').read_text())
    assert case['phase']=='SHIFT' and case['observed_gripper_peak_mps']>.005
    value=owner(nav_robot_model);value.phase='SHIFT';value._phase_start=1_000_000_000
    value._crawl_reference_time(1_000_000_000,2_000_000_000,0)
    gap=case['cadence_probe_ns']
    # The recorded native hold/step motivates this cadence probe; native sample
    # times are NOT exact publisher callbacks. Physical coupling remains gated
    # by actual fixed-source native G2, not this deterministic time-law test.
    elapsed,step=value._crawl_reference_time(1_000_000_000+gap,2_000_000_000+gap,gap)
    assert round(step*1e9)<=case['reference_step_cap_ns']
    assert elapsed==step==.04
    assert value._crawl_shift_clock['max_step_ns']==40_000_000


def test_shift_budget_policy_does_not_enlarge_delayed_swing_reference(nav_robot_model):
    value=owner(nav_robot_model);legacy=CrawlMachine(nav_robot_model,default_limits())
    for machine in (value,legacy):
        machine.phase='SWING';machine._phase_start=1_000_000_000
        machine._crawl_reference_time(1_000_000_000,2_000_000_000,0)
    # Original 242efeba native window: 90.239ms command interval during RL SWING;
    # later native calf reference steps reached 0.006986rad and jaw speed .005889m/s.
    args=(1_092_000_000,2_090_239_003,90_239_003)
    actual=value._crawl_reference_time(*args)
    expected=legacy._crawl_reference_time(*args)
    assert actual==expected==(0.02,0.02),'SHIFT budget correction expanded the SWING reference step'


def test_original_failed_cadence_can_sample_same_curve_without_impossible_reference_count(nav_robot_model):
    fixture=json.loads((Path(__file__).parent/'fixtures/reference-4163.json').read_text())
    value=owner(nav_robot_model);legacy=CrawlMachine(nav_robot_model,default_limits())
    for machine in (value,legacy):
        machine.phase='SHIFT';machine._phase_start=1_000_000_000
    times=[];old_times=[];previous=(0,0)
    for ros,wall in fixture['decisions']:
        # These are offsets of the original 101 issued decisions, not invented
        # faster transport. ACK ownership is independently tested over DDS.
        elapsed,step=value._crawl_reference_time(1_000_000_000+ros,2_000_000_000+wall,
            min(ros-previous[0],wall-previous[1]))
        old,_=legacy._crawl_reference_time(1_000_000_000+ros,2_000_000_000+wall,
            min(ros-previous[0],wall-previous[1]))
        assert step*1e9<=min(200_000_000,ros-previous[0],wall-previous[1])+1e-6
        times.append(elapsed);old_times.append(old);previous=(ros,wall)
    assert len(times)==101 and old_times[-1]<fixture['required_reference_ns']/1e9
    assert times[-1]>=fixture['required_reference_ns']/1e9
    assert times[-1]<=min(*fixture['decisions'][-1])/1e9+1e-12
    # Mean-value bound of the unchanged quintic, measured over BOTH real clocks.
    duration=fixture['required_reference_ns']/1e9;distance=.027
    prior_t=prior_x=0.;prior_clock=(0,0)
    for elapsed,(ros,wall) in zip(times,fixture['decisions']):
        point=distance*blend(elapsed/duration)
        dt=min(ros-prior_clock[0],wall-prior_clock[1])/1e9
        if dt>0:assert abs(point-prior_x)/dt<=1.875*distance/duration+1e-12
        prior_t,prior_x,prior_clock=elapsed,point,(ros,wall)


def test_no_credit_still_holds_reference_and_original_sensor_expiry(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.))
    value.reference_time_policy='applied_shift_elapsed'
    held=value.reference_body.copy();targets=deepcopy(value._targets)
    ros,wall=value._last_ros+40_000_000,value._last_wall+40_000_000
    result=value.advance(sample_at(plant.state,ros,wall),(.01,0.,0.),ros,wall,reference_permitted=False)
    assert result.state=='CRAWL' and result.joint_targets is None
    assert np.array_equal(value.reference_body,held)
    assert all(np.array_equal(value._targets[key],target) for key,target in targets.items())
    result=value.advance(plant.state,(.01,0.,0.),ros+200_000_001,wall+200_000_001)
    assert result.state=='FAULT' and result.reason=='control gap'


def test_elapsed_policy_never_extrapolates_original_ros_or_extends_phase_deadline(nav_robot_model):
    value=owner(nav_robot_model);value.phase='SHIFT';value._phase_start=1_000_000_000
    elapsed,step=value._crawl_reference_time(1_018_000_000,2_020_000_000,18_000_000)
    assert elapsed==.018 and step==.018
    held,_=value._crawl_reference_time(1_018_000_000,2_060_000_000,0,False)
    assert held==elapsed
    machine,plant=shifting(nav_robot_model,(.01,0.,0.))
    machine.reference_time_policy='applied_shift_elapsed'
    machine._phase_start=plant.ros-int((machine._shift_duration+1.1)*1e9)
    machine._unload_start=None;machine._shift_settled_start=None
    result=machine.advance(sample_at(plant.state,plant.ros,plant.wall),(.01,0.,0.),plant.ros,plant.wall)
    assert result.state=='FAULT' and 'shift timeout' in result.reason and result.joint_targets is None


def test_same_swing_curve_keeps_analytic_speed_bound_at_original_irregular_samples(nav_robot_model):
    data=json.loads((Path(__file__).parent/'fixtures/reference-4163.json').read_text())
    value=owner(nav_robot_model);value.phase='SWING';value._phase_start=1_000_000_000
    legacy=CrawlMachine(nav_robot_model,default_limits());legacy.phase='SWING';legacy._phase_start=1_000_000_000
    delta=np.asarray([.01,-.005,.002]);amplitude=.01;speed=.02
    duration=max(.8,(1.875*np.linalg.norm(delta)+16/(3*math.sqrt(3))*amplitude)/speed)
    prior_point=np.zeros(3);prior_clock=(0,0);elapsed=0.
    for ros,wall in data['decisions']:
        elapsed,step=value._crawl_reference_time(1_000_000_000+ros,2_000_000_000+wall,
            min(ros-prior_clock[0],wall-prior_clock[1]))
        assert (elapsed,step)==legacy._crawl_reference_time(1_000_000_000+ros,2_000_000_000+wall,
            min(ros-prior_clock[0],wall-prior_clock[1]))
        u=min(1.,elapsed/duration);point=delta*blend(u)
        point[2]+=amplitude*16*u*u*(1-u)*(1-u)
        dt=min(ros-prior_clock[0],wall-prior_clock[1])/1e9
        if dt>0:assert np.linalg.norm(point-prior_point)/dt<=speed+1e-12
        prior_point,prior_clock=point,(ros,wall)
    # Synthetic continuation only verifies the original endpoint; it is not a
    # claim that the original 101 native decisions completed this swing.
    while elapsed<duration:
        ros+=20_000_000;wall+=20_000_000
        elapsed,step=value._crawl_reference_time(1_000_000_000+ros,2_000_000_000+wall,20_000_000)
        assert step<=.02
    u=min(1.,elapsed/duration);point=delta*blend(u)
    point[2]+=amplitude*16*u*u*(1-u)*(1-u)
    assert np.allclose(point,delta,atol=1e-12)


@pytest.mark.parametrize('g2',[False,True])
def test_real_ros_owner_selects_elapsed_policy_only_in_acknowledged_g2_scope(tmp_path,nav_robot_model,g2):
    import rclpy
    from rclpy.context import Context
    from lifecycle_msgs.msg import Transition
    from test_execution_admission_contract import fixture
    from test_g2_control_cadence_ros import controller
    from test_crawl_lifecycle import CrawlRig
    profile,expected=fixture(tmp_path,nav_robot_model,'mujoco')
    ctx=Context();rclpy.init(context=ctx);node=controller(ctx,nav_robot_model,profile,expected,g2=g2)
    rig=CrawlRig(node,nav_robot_model,ctx)
    from rosgraph_msgs.msg import Clock
    rig.node.destroy_publisher(rig.clock)
    rig.clock=rig.node.create_publisher(Clock,'/navigation/control_clock',10)
    try:
        rig.pump(.3)
        assert rig.transition(Transition.TRANSITION_CONFIGURE)
        assert node.machine.reference_time_policy==('applied_shift_elapsed' if g2 else 'bounded_20ms')
        assert (node.applied_credit is not None)==g2
        assert not node.active and not rig.commands
    finally:rig.close();ctx.try_shutdown()
