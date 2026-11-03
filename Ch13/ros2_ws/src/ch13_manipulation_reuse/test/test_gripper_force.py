import pytest
from ch13_manipulation_reuse.gripper_force import ForceHold,servo_reference


def test_same_native_pd_produces_requested_bounded_force():
    reference=servo_reference(0.,.02,.001,10.,.8,.5,1.)
    assert 10*(reference-.02)-.8*.001==pytest.approx(-.5)
    assert servo_reference(0.,.02,0.,10.,.8,.5,0.)==0.
    with pytest.raises(ValueError):servo_reference(0.,.02,0.,10.,.8,.51,1.)


def update(hold,t,contacts,*,allowed=True,nominal=0.):
    return hold.update(t,'CLOSE',nominal,.5,contacts,.02,0.,10.,.8,allowed)


def test_only_continuous_dual_contact_can_start_force_hold():
    hold=ForceHold()
    update(hold,1.,{'link7':.1,'link8':0.});assert hold.start is None
    update(hold,2.,{'link7':.1,'link8':.1},allowed=False);assert hold.start is None
    update(hold,3.,{'link7':.1,'link8':.1});assert hold.start is None
    update(hold,3.3,{'link7':.1,'link8':.1});assert hold.start==3.3
    assert update(hold,3.8,{'link7':.1,'link8':.1})==pytest.approx(-.03)


def test_fault_retains_established_force_but_explicit_open_clears_it():
    hold=ForceHold();contacts={'link7':.1,'link8':.1}
    update(hold,1.,contacts);update(hold,1.3,contacts)
    assert update(hold,2.,{},allowed=False)==pytest.approx(-.03)
    assert update(hold,2.1,{},allowed=False,nominal=.03)==.03
    assert hold.start is None
