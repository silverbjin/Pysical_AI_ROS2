"""G1 return command smoothness; not proof of physical carry stability."""
import numpy as np
from test_inplace_calibration import trajectory,tick


def test_planned_return_brakes_without_acceleration_steps_or_new_speed_budget():
    value=trajectory(start_z=.030)
    value.phase='TOUCHDOWN';value.velocity=.02
    previous=value.velocity;accelerations=[0.];positions=[value.z]
    # Loaded retiming may exceed the old2.4s illustration. The actual10s
    # deadline and full owner settle remain the binding completion budget.
    for index in range(1,400):
        result=tick(value,index,forces=(30.,5.,30.,30.))
        accelerations.append((value.velocity-previous)/.02)
        assert abs(value.velocity)<=.020000001
        assert abs(result.z-positions[-1])<=.02*.02000001
        positions.append(result.z);previous=value.velocity
        if result.complete:break
    assert result.complete and result.z==value.rest_z and value.velocity==0.
    assert value.last_wall+1_000_000_000<value.deadline
    assert max(abs(a) for a in accelerations)<=.20000001
    # Existing .02m/s and .2m/s² permit a quintic velocity ramp with T=.1875s.
    # Its analytic jerk max is (10sqrt(3)/3)*.02/T² <3.285m/s³; allow discrete
    # samples 4.0, while the old acceleration step produces10m/s³.
    jerk=np.diff(accelerations)/.02
    assert max(abs(jerk))<=4., 'return has an acceleration step that can excite the loaded arm'
