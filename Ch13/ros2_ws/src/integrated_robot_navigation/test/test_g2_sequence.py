"""Ideal arithmetic fixtures only; movement acceptance still requires engines."""
from dataclasses import asdict,replace
import importlib.util
import math
import pytest
from guard_fixture import bundle
from integrated_robot_navigation.carry_profile import default_limits


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.g2_sequence'),'measured G2 sequence missing'
    from integrated_robot_navigation import g2_sequence
    return g2_sequence


def test_snapshot_uses_native_body_and_rejects_capture_or_wall_expiry(nav_robot_model):
    value=bundle(nav_robot_model);frame=dict(samples=asdict(value),crawl=dict(stopped=True))
    body=value.body
    result=api().movement_snapshot(frame,body.stamp_ns,body.received_ns,default_limits())
    assert result['pose'][:2]==tuple(body.data['position'][:2])
    for ros,wall in ((body.stamp_ns+200000001,body.received_ns),(body.stamp_ns,body.received_ns+200000001)):
        with pytest.raises(ValueError):api().movement_snapshot(frame,ros,wall,default_limits())


class IdealSequence:
    def __init__(self,*,stop_feedback=True):
        self.pose=[0.,0.,0.];self.velocity=(0.,0.);self.smoothed=(0.,0.)
        self.capture=1_000_000_000;self.wall=1_000_000_000
        self.stop_feedback=stop_feedback;self.commands=[];self.stages=[]
        self.current_stage='stand'
    def set_stage(self,value):self.current_stage=value;self.stages.append(value)
    def set_target(self,vx,wz):self.velocity=self.smoothed=(vx,wz);self.commands.append((vx,wz))
    def mode(self,name):return True
    def snapshot(self):
        return dict(pose=tuple(self.pose),capture_ns=self.capture,wall_ns=self.wall,stage=self.current_stage,
            motion_state='CRAWL' if self.velocity!=(0.,0.) else 'STOPPED',
            stopped=self.stop_feedback and self.velocity==(0.,0.),linear_speed=abs(self.velocity[0]),
            yaw_speed=abs(self.velocity[1]),touching=(True,)*4)
    def wait(self,predicate,seconds,label):
        end=self.wall+int(seconds*1e9)
        while not predicate():
            if self.wall>=end:raise TimeoutError(label)
            dt=.02;vx,wz=self.velocity
            self.pose[0]+=math.cos(self.pose[2])*vx*dt;self.pose[1]+=math.sin(self.pose[2])*vx*dt
            self.pose[2]+=wz*dt;self.capture+=20_000_000;self.wall+=20_000_000


def test_sequence_requires_measured_forward_both_yaws_and_final_settle():
    plant=IdealSequence();result=api().run_sequence('crawl-cycle',snapshot=plant.snapshot,
        source=plant,mode=plant.mode,wait=plant.wait,set_stage=plant.set_stage,limits=default_limits())
    assert set(result)=={'forward','left','right','stopped'}
    assert result['forward']['end'][0]>=.4
    assert result['left']['end'][2]-result['left']['start'][2]>=.3
    assert result['right']['end'][2]-result['right']['start'][2]<=-.3
    assert plant.commands[-1]==(0.,0.)


def test_stand_ack_without_measured_stop_never_completes_a_phase():
    plant=IdealSequence(stop_feedback=False)
    with pytest.raises(TimeoutError,match='settle'):
        api().run_sequence('crawl-reverse',snapshot=plant.snapshot,source=plant,
            mode=plant.mode,wait=plant.wait,set_stage=plant.set_stage,limits=default_limits())
    assert plant.commands[-1]==(0.,0.)


def test_rejected_crawl_mode_sends_no_moving_target():
    plant=IdealSequence()
    with pytest.raises(RuntimeError,match='CRAWL'):
        api().run_sequence('crawl-cycle',snapshot=plant.snapshot,source=plant,mode=lambda _:False,
            wait=plant.wait,set_stage=plant.set_stage,limits=default_limits())
    assert not any(vx or wz for vx,wz in plant.commands)


def test_unhealthy_status_resets_settle_even_when_the_body_capture_is_duplicated():
    value=api().MeasuredSettle(default_limits())
    def row(capture,wall,stopped=True):
        return dict(capture_ns=capture,wall_ns=wall,stopped=stopped,
            linear_speed=0.,yaw_speed=0.,touching=(True,)*4)
    assert not value.update(row(1_000_000_000,1_000_000_000))
    assert not value.update(row(1_000_000_000,1_050_000_000,False))
    assert not value.update(row(1_100_000_000,1_100_000_000))
    assert not value.update(row(2_000_000_000,2_000_000_000))


class LatchedStandSequence(IdealSequence):
    """Model the existing explicit-stop latch, not an ideal mode acceptance."""
    def __init__(self):super().__init__();self.latched=False;self.modes=[]
    def mode(self,name):
        self.modes.append(name)
        if name=='STAND':self.latched=True
        return True  # guard acceptance does not clear the leg owner's latch
    def set_target(self,vx,wz):
        super().set_target(vx,wz)
        if self.latched:self.velocity=(0.,0.)


def test_intermediate_measured_pause_preserves_authority_without_clearing_explicit_stop():
    plant=LatchedStandSequence()
    result=api().run_sequence('crawl-cycle',snapshot=plant.snapshot,source=plant,mode=plant.mode,
        wait=plant.wait,set_stage=plant.set_stage,limits=default_limits())
    assert set(result)=={'forward','left','right','stopped'}
    assert plant.modes==['CRAWL','CRAWL','CRAWL','STAND']
    assert plant.latched, 'the final explicit stop is retained'


def test_mode_acceptance_without_crawl_state_fails_before_the_long_motion_deadline():
    plant=LatchedStandSequence();plant.latched=True;start=plant.wall
    with pytest.raises(TimeoutError,match='motion state'):
        api().run_sequence('crawl-cycle',snapshot=plant.snapshot,source=plant,mode=plant.mode,
            wait=plant.wait,set_stage=plant.set_stage,limits=default_limits())
    assert plant.wall-start<=2_100_000_000
    assert plant.commands[-1]==(0.,0.)
