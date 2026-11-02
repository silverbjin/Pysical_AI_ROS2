"""Break: a complete support search blocks the short safety/control callback."""
import numpy as np
import pytest

from integrated_robot_navigation import gait
from integrated_robot_navigation.carry_profile import default_limits
from gait_fixture import IdealFeedback


@pytest.mark.parametrize('calibration,candidate_budget',[(True,4),(False,1)])
@pytest.mark.parametrize('load_policy',['geometric','stance_admittance'])
def test_support_search_is_sliced_across_fresh_safety_ticks(nav_robot_model, monkeypatch,calibration,candidate_budget,load_policy):
    if load_policy=='stance_admittance':
        from test_stance_load_transfer import helper
        nav_robot_model=helper(nav_robot_model).model
    plant = IdealFeedback(nav_robot_model)
    machine = gait.CrawlMachine(nav_robot_model, default_limits(),load_transfer_policy=load_policy)
    machine.reset(plant.state, plant.ros, plant.wall)
    if calibration:machine.request_contact_calibration()
    actual_com = gait.center_of_mass
    evaluations = []

    def measured_cost(*args):
        evaluations.append(None)
        return actual_com(*args)

    monkeypatch.setattr(gait, 'center_of_mass', measured_cost)
    initial = machine.reference_body.copy()
    moved = False
    for tick in range(45):
        before = len(evaluations)
        result = machine.advance(plant.state, (0., 0., 0.) if calibration else (.001,0.,0.), plant.ros, plant.wall)
        assert result.state != 'FAULT', result.reason
        # One actual measurement plus the bounded role-specific candidate count.
        # Normal CRAWL stays at one; G1-only arithmetic batching uses four.
        assert len(evaluations)-before <= 1+candidate_budget
        if tick < 2:
            assert machine.reference_body == pytest.approx(initial, abs=1e-12)
        moved |= np.linalg.norm(machine.reference_body[:2, 3]-initial[:2, 3]) > 1e-5
        plant.tick(machine, result)
    assert moved, 'bounded planning must eventually progress, not freeze indefinitely'


def test_expired_feedback_aborts_a_pending_plan_without_new_commands(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    machine = gait.CrawlMachine(nav_robot_model, default_limits())
    machine.reset(plant.state, plant.ros, plant.wall)
    machine.request_contact_calibration()
    machine.advance(plant.state, (0., 0., 0.), plant.ros, plant.wall)
    result = machine.advance(plant.state, (0., 0., 0.), plant.ros+200_000_001, plant.wall+200_000_001)
    assert result.state == 'FAULT' and result.joint_targets is None


def test_stop_discards_a_pending_search_without_starting_a_lift(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    machine = gait.CrawlMachine(nav_robot_model, default_limits())
    machine.reset(plant.state, plant.ros, plant.wall)
    machine.request_contact_calibration()
    machine.advance(plant.state, (0., 0., 0.), plant.ros, plant.wall)
    initial = machine.reference_body.copy()
    machine.request_stop(urgent=True)
    for _ in range(70):
        plant.tick(follow=False)
        result = machine.advance(plant.state, (0., 0., 0.), plant.ros, plant.wall)
        assert result.swing_foot is None and result.state != 'FAULT'
        assert machine.reference_body == pytest.approx(initial, abs=1e-12)
    assert result.state == 'STOPPED'
