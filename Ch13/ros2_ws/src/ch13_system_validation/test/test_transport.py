import pytest
from ch13_system_validation.transport import TransportLease


def message(phase='HOLD',seq=1,**kw):
    return dict(session='s',goal_id='outbound',sequence=seq,stamp_ns=1_000_000_000,
                terminal=4,target=[1.,0.,0.],capture_ns=1_000_000_000,state='OFFER',
                task_phase=phase,**kw)


def live():
    lease=TransportLease('s')
    sample=dict(capture_ns=1_000_000_000,capture_wall=10.,first_receipt_wall=10.01,
                tf_stamp_ns=980_000_000,source_gids={'rgb':'a'},rgb_sha256='a'*64,point=[1.5,0.,.6])
    lease.observe(sample,'observer',10.02)
    lease.motion_inputs(armed=True,moving_supported=True,contacts=True,busy=False,support=False)
    lease.heartbeat(message(),'owner',10.03)
    assert evaluate(lease)=='READY'
    return lease


def evaluate(lease,goals=None,settled=True,idle=True,pose=None):
    return lease.evaluate(1_100_000_000,10.1,settled=settled,supported=True,
        goal_status={'outbound':4} if goals is None else goals,actual_pose=[1.,0.,0.] if pose is None else pose,navigation_idle=idle)


def arm(lease):
    lease.heartbeat(message('CARRY_ARMED',2,transport_goal_id='home',transport_target=[0.,0.,3.14]),'owner',10.04)
    return evaluate(lease)


def test_reserved_return_goal_allowed_but_arm_actions_are_not_ready_during_transport():
    lease=live();assert arm(lease)=='CARRY_ARMED'
    lease.heartbeat(message('CARRY',3,transport_goal_id='home',transport_target=[0.,0.,3.14]),'owner',10.05)
    assert evaluate(lease,{'outbound':4,'home':2},settled=False,idle=False)=='CARRY'


def test_unknown_goal_still_latches_fault():
    lease=live();arm(lease)
    assert evaluate(lease,{'outbound':4,'intruder':2})=='FAULT'
    assert lease.fault=='UNRESERVED_NAV_GOAL'


@pytest.mark.parametrize('field', ['contacts','moving_supported','armed'])
def test_transport_health_loss_faults(field):
    lease=live();arm(lease)
    values=dict(armed=True,moving_supported=True,contacts=True,busy=False,support=False)
    values[field]=False;lease.motion_inputs(**values)
    assert evaluate(lease)=='FAULT'


def test_busy_arm_cannot_enter_transport():
    lease=live();lease.motion_inputs(armed=True,moving_supported=True,contacts=True,busy=True,support=False)
    assert arm(lease)=='FAULT'


def test_place_request_requires_actual_return_terminal_and_settling():
    lease=live();arm(lease)
    lease.heartbeat(message('CARRY',3,transport_goal_id='home',transport_target=[0.,0.,3.14]),'owner',10.05)
    evaluate(lease,{'outbound':4,'home':2},False,False)
    lease.heartbeat(message('PLACE_WAIT',4,transport_goal_id='home',transport_target=[0.,0.,3.14]),'owner',10.06)
    assert evaluate(lease,{'outbound':4,'home':2},False,False)!='READY'
    assert evaluate(lease,{'outbound':4,'home':4},True,True,pose=[0.,0.,3.14])=='READY'


def test_stale_original_observation_never_authorizes_carry():
    lease=live();arm(lease)
    assert lease.evaluate(1_500_000_000,10.5,settled=False,supported=False,
        goal_status={'outbound':4,'home':2},actual_pose=[.8,0.,0.],navigation_idle=False)=='FAULT'


def test_revoke_remains_terminal_in_transport():
    lease=live();arm(lease)
    request=message('CARRY',3,transport_goal_id='home',transport_target=[0.,0.,3.14]);request['state']='REVOKE'
    lease.heartbeat(request,'owner',10.05)
    assert evaluate(lease)=='REVOKED'
    arm(lease);assert evaluate(lease)=='REVOKED'


@pytest.mark.parametrize('payload',[None,[],True])
def test_non_object_heartbeat_latches_instead_of_escaping_callback(payload):
    lease=live();arm(lease)
    lease.heartbeat(payload,'owner',10.05)
    assert lease.phase=='FAULT'


def test_release_rejected_before_return_stationary_authority():
    lease=live();arm(lease)
    lease.heartbeat(message('RELEASE',3,transport_goal_id='home',transport_target=[0.,0.,3.14]),'owner',10.05)
    assert lease.phase=='FAULT'
