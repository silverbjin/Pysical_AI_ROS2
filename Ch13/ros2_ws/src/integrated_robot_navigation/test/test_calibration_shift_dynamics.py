"""G1 timing hypothesis; mathematical reference test, not contact/G1 proof."""
import math
import numpy as np
from gait_fixture import IdealFeedback
from test_gait import machine


def test_g1_uses_half_acceleration_without_changing_normal_shift_geometry_or_limits(nav_robot_model):
    plant=IdealFeedback(nav_robot_model)
    normal,calibration=(machine(nav_robot_model,plant) for _ in range(2))
    calibration.request_contact_calibration()
    for value in (normal,calibration):
        q,_,_,loads,points,com=value._measure(plant.state,plant.ros,plant.wall)
        value._begin_shift(com,loads,points,plant.ros,q)
        list(value._shift_plan)
    assert np.allclose(normal._offset_goal,calibration._offset_goal,atol=1e-12)
    assert normal.limits==calibration.limits
    assert math.isclose(calibration._shift_duration/normal._shift_duration,math.sqrt(2),rel_tol=1e-9)
    distance=np.linalg.norm(calibration._offset_goal-calibration._offset_start)
    peak_accel=(10*math.sqrt(3)/3)*distance/calibration._shift_duration**2
    assert peak_accel<=.5*normal.limits['max_support_shift_accel_mps2']+1e-12
