"""Break: a 20mm/80mm target envelope alone does not bound foot speed."""
import numpy as np
import pytest

from gait_fixture import IdealFeedback
from test_gait import machine


@pytest.mark.parametrize('command', [(0., 0., 0.), (.01, 0., 0.), (0., 0., .03)])
def test_world_foot_swing_reference_is_quasistatic_and_still_completes(nav_robot_model, command):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    if command == (0., 0., 0.):
        value.request_contact_calibration()
    previous, began = None, None
    finished = False
    for _ in range(1500):  # bounded 30s observation, not a fixed cycle success claim
        result = value.advance(plant.state, command, plant.ros, plant.wall)
        assert result.state != 'FAULT', result.reason
        if result.phase == 'SWING':
            began = plant.ros if began is None else began
            position = value._targets[result.swing_foot].copy()
            if previous is not None:
                assert np.linalg.norm(position-previous)/.02 <= .020000001, \
                    'quasistatic foot speed must not depend on an arbitrary .8s timer'
            previous = position
        elif began is not None and result.phase == 'TOUCHDOWN':
            finished = True
            break
        plant.tick(value, result)
    assert finished, 'a speed cap must not silently freeze or abandon the active foot'
