import copy
import pytest
from ch13_manipulation_reuse.lease import Lease


def observation(stamp=1_000_000_000, wall=10.):
    return dict(capture_ns=stamp, capture_wall=wall, first_receipt_wall=wall+.01,
                tf_stamp_ns=stamp-20_000_000, source_gids={'rgb':'a','depth':'b'},
                rgb_sha256='a'*64, point=[1.,0.,.5])


def heartbeat(seq=1, session='engine-a', goal='goal-a', stamp=1_000_000_000):
    return dict(session=session, goal_id=goal, sequence=seq, stamp_ns=stamp,
                terminal=4, target=[0.,0.,0.], capture_ns=stamp, state='OFFER')


def evaluate(lease, *, settled=True, wall=10.10, clock=1_100_000_000, goals=None):
    return lease.evaluate(clock, wall, settled=settled, supported=True,
                          goal_status={'goal-a':4} if goals is None else goals,
                          actual_pose=[0.,0.,0.], navigation_idle=True)


def offered():
    lease=Lease('engine-a')
    lease.observe(observation(),'observer',10.02)
    lease.heartbeat(heartbeat(),'mission',10.03)
    return lease


def test_live_terminal_actual_settle_required():
    lease=offered()
    assert evaluate(lease,settled=False)=='WAITING'
    assert evaluate(lease)=='READY'
    assert lease.goal_id=='goal-a'


def test_old_session_never_authorizes():
    lease=Lease('engine-b')
    lease.observe(observation(),'observer',10.02)
    lease.heartbeat(heartbeat(),'mission',10.03)
    assert evaluate(lease)=='FAULT'
    assert lease.fault=='SESSION_MISMATCH'


def test_summary_terminal_does_not_replace_live_action_status():
    assert evaluate(offered(),goals={})=='WAITING'


def test_repeat_capture_cannot_renew_original_age():
    lease=offered()
    assert evaluate(lease)=='READY'
    lease.observe(observation(),'observer',10.29)
    lease.heartbeat(heartbeat(seq=2),'mission',10.29)
    assert evaluate(lease,wall=10.31,clock=1_200_000_000)=='FAULT'
    assert lease.fault=='OBSERVATION_EXPIRED'


@pytest.mark.parametrize('channel',['mission','observer'])
def test_replaced_owner_latches(channel):
    lease=offered()
    if channel=='mission':lease.heartbeat(heartbeat(seq=2),'new-owner',10.04)
    else:lease.observe(observation(),'new-owner',10.04)
    assert evaluate(lease)=='FAULT'
    assert 'OWNER' in lease.fault


def test_stale_tf_and_nonfinite_are_rejected():
    for field,value in [('tf_stamp_ns',800_000_000),('capture_wall',float('nan'))]:
        lease=Lease('engine-a');sample=observation();sample[field]=value
        lease.observe(sample,'observer',10.02)
        assert lease.fault


def test_replay_does_not_renew_heartbeat():
    lease=offered();assert evaluate(lease)=='READY'
    lease.heartbeat(heartbeat(),'mission',10.29)
    assert evaluate(lease,wall=10.34)=='FAULT'
    assert lease.fault=='MISSION_EXPIRED'


def test_new_goal_or_navigation_cancels_live_permission():
    lease=offered();assert evaluate(lease)=='READY'
    assert evaluate(lease,goals={'goal-a':4,'other':2})=='FAULT'
    assert lease.fault=='NEW_NAV_GOAL'


def test_explicit_revoke_and_no_automatic_return():
    lease=offered();assert evaluate(lease)=='READY'
    msg=heartbeat(seq=2);msg['state']='REVOKE'
    lease.heartbeat(msg,'mission',10.11)
    assert evaluate(lease)=='REVOKED'
    lease.heartbeat(heartbeat(seq=3),'mission',10.12)
    assert evaluate(lease)=='REVOKED'


def test_execution_checks_base_support_instead_of_arm_stationarity():
    lease=offered();assert evaluate(lease)=='READY'
    lease.begin_execution()
    assert evaluate(lease,settled=False)=='EXECUTING'
    assert lease.evaluate(1_100_000_000,10.12,settled=False,supported=False,
                          goal_status={'goal-a':4},actual_pose=[0.,0.,0.],navigation_idle=True)=='FAULT'


def test_wall_and_sim_clock_rollback_latch():
    for clock,wall in [(1_000_000_000,10.11),(1_200_000_000,10.09)]:
        lease=offered();assert evaluate(lease)=='READY'
        assert evaluate(lease,clock=clock,wall=wall)=='FAULT'


def test_invalid_heartbeat_and_outside_goal_pose_do_not_admit():
    lease=offered();msg=heartbeat(seq=2);msg['target']=[float('nan'),0.,0.]
    lease.heartbeat(msg,'mission',10.04)
    assert evaluate(lease)=='FAULT'
    lease=offered()
    assert lease.evaluate(1_100_000_000,10.1,settled=True,supported=True,
                          goal_status={'goal-a':4},actual_pose=[.11,0.,0.],navigation_idle=True)=='WAITING'
