import numpy as np
import pytest
from ch13_sim_core.contract import load_contract
from ch13_sim_core.arbiter import CommandArbiter, GroupCommand

@pytest.fixture
def arb(): return CommandArbiter(load_contract())

def cmd(arb, group='arm', stamp=1., owner='one', values=None):
    g = arb.contract.groups[group]
    return GroupCommand(g.names, np.array(g.nominal if values is None else values), stamp, owner)

def test_resolves_twenty_by_name_and_clips(arb):
    arb.resolve(1.)
    g = arb.contract.groups['arm']
    arb.update('arm',GroupCommand(g.names[::-1],np.array([0,0,0,0,.2,99]),1.,'one'))
    r=arb.resolve(1.1)
    assert r.targets.shape == (20,)
    np.testing.assert_allclose(r.targets[12:14],[3.14,.2])

@pytest.mark.parametrize('names,values',[(('fr_hip_joint',)*6,[0]*6),(('arm_joint_1',)*6,[0]*6),(tuple(f'arm_joint_{i}' for i in range(1,7)),[0,0,0,0,0,float('nan')])])
def test_rejects_without_mutation(arb,names,values):
    before=arb.resolve(1.).targets.copy()
    with pytest.raises(ValueError): arb.update('arm',GroupCommand(names,np.array(values),1.,'one'))
    np.testing.assert_array_equal(arb.resolve(1.).targets,before)

def test_owner_conflict_and_explicit_reset(arb):
    arb.resolve(1.)
    arb.update('arm',cmd(arb))
    with pytest.raises(ValueError,match='owner'): arb.update('arm',cmd(arb,owner='two',values=[.1]*6))
    np.testing.assert_array_equal(arb.resolve(1.01).targets[12:18],[0]*6)
    arb.reset_owner('arm')
    arb.update('arm',cmd(arb,stamp=1.01,owner='two',values=[.1]*6))
    np.testing.assert_allclose(arb.resolve(1.02).targets[12:18],[.1]*6)

def test_stale_future_and_time_reversal_hold_safe(arb):
    arb.resolve(1.)
    with pytest.raises(ValueError): arb.update('arm',cmd(arb,stamp=2.))
    arb.update('arm',cmd(arb,values=[.1]*6))
    arb.resolve(1.02)
    assert 'arm' in arb.resolve(2.).stale_groups
    np.testing.assert_allclose(arb.resolve(2.).targets[12:18],[.1]*6)
    with pytest.raises(ValueError): arb.update('arm',cmd(arb,stamp=.9))
    assert arb.resolve(.5).status == 'clock_reversed'

def test_rejected_future_command_cannot_poison_owner(arb):
    arb.resolve(0.)
    with pytest.raises(ValueError): arb.update('arm',cmd(arb,stamp=10.,owner='bad'))
    arb.update('arm',cmd(arb,stamp=0.,owner='good'))

def test_input_and_result_arrays_are_copied(arb):
    arb.resolve(1.)
    c=cmd(arb)
    arb.update('arm',c)
    c.positions[:]=2
    r=arb.resolve(1.02)
    r.targets[:]=2
    np.testing.assert_allclose(arb.resolve(1.04).targets[12:18],[0]*6)

@pytest.mark.parametrize('stamp',[0.,1000.])
def test_no_command_can_claim_owner_before_trusted_clock(arb,stamp):
    with pytest.raises(ValueError,match='clock'):arb.update('arm',cmd(arb,stamp=stamp,owner='bad',values=[1.]*6))
    arb.resolve(1.)
    arb.update('arm',cmd(arb,owner='good',values=[.1]*6))
    np.testing.assert_allclose(arb.resolve(1.02).targets[12:18],[.1]*6)

def test_frozen_clock_holds_pending_targets_until_resume(arb):
    arb.resolve(1.)
    arb.update('arm',cmd(arb,values=[.2]*6))
    np.testing.assert_array_equal(arb.resolve(1.).targets[12:18],[0]*6)
    np.testing.assert_allclose(arb.resolve(1.02).targets[12:18],[.2]*6)
    arb.update('arm',cmd(arb,stamp=1.02,values=[.3]*6))
    np.testing.assert_allclose(arb.resolve(1.02).targets[12:18],[.2]*6)
    np.testing.assert_allclose(arb.resolve(1.04).targets[12:18],[.3]*6)

def test_stale_pending_command_never_becomes_last_safe_target(arb):
    arb.resolve(1.)
    arb.update('arm',cmd(arb,values=[.4]*6))
    np.testing.assert_array_equal(arb.resolve(2.).targets[12:18],[0]*6)
