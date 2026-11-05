import math
import pytest
from ch13_system_validation.place_settling import PlacementSupportGate


def test_action_success_and_stationary_arm_do_not_substitute_for_support():
    gate=PlacementSupportGate()
    # v17 action terminal had <.003rad/s, yet the can remained 1.79mm high.
    assert not gate.update(0,[.001856]*6,True,0.)
    assert not gate.update(2_442_000_000,[.001]*6,True,.0149)
    assert not gate.update(2_941_000_000,[.001]*6,True,.02)
    assert gate.update(2_942_000_000,[.001]*6,True,.02)


@pytest.mark.parametrize('velocity,stationary,support',[
    ([.004]*6,True,.02),([0.]*6,False,.02),([0.]*6,True,0.),
    ([0.]*6,True,float('nan')),([0.]*5,True,.02),([math.inf]*6,True,.02)])
def test_support_hold_resets_on_motion_loss_or_invalid_measurements(velocity,stationary,support):
    gate=PlacementSupportGate()
    assert not gate.update(0,[0.]*6,True,.02)
    assert not gate.update(400_000_000,velocity,stationary,support)
    assert not gate.update(500_000_000,[0.]*6,True,.02)
    assert gate.update(1_000_000_000,[0.]*6,True,.02)


def test_backward_clock_cannot_complete_hold():
    gate=PlacementSupportGate()
    assert not gate.update(1_000_000_000,[0.]*6,True,.02)
    assert not gate.update(0,[0.]*6,True,.02)
    assert not gate.update(400_000_000,[0.]*6,True,.02)
    assert gate.update(500_000_000,[0.]*6,True,.02)
