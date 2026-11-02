"""The combined moving-body reference needs the same configured accel bound.

Zero-command G1 checks the support offset alone and cannot establish this.
Ideal feedback is used only for reference arithmetic, not physical stability.
"""
import numpy as np
import math
import pytest
from gait_fixture import IdealFeedback
from test_gait import machine


@pytest.mark.parametrize('command',[(.01,0.,0.),(-.01,0.,0.),(0.,0.,.03),(.007,0.,.02)])
@pytest.mark.parametrize('ramped',[False,True])
def test_normal_crawl_body_travel_plus_support_shift_respects_acceleration(nav_robot_model,command,ramped):
    plant=IdealFeedback(nav_robot_model)
    value=machine(nav_robot_model,plant)
    positions=[];phases=[];yaws=[];started=plant.ros
    for _ in range(2200):
        elapsed=(plant.ros-started)/1e9
        current=(math.copysign(min(abs(command[0]),value.limits['max_accel_x']*elapsed),command[0]),0.,
                 math.copysign(min(abs(command[2]),value.limits['max_accel_wz']*elapsed),command[2])) if ramped else command
        result=value.advance(plant.state,current,plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        positions.append(value.reference_body[:2,3].copy());phases.append(result.phase)
        yaws.append(math.atan2(value.reference_body[1,0],value.reference_body[0,0]))
        plant.tick(value,result)
        if value._index==2 and len(positions)>4:break
    acceleration=np.linalg.norm(np.diff(np.array(positions),n=2,axis=0)/.02**2,axis=1)
    index=int(np.argmax(acceleration))+1
    assert acceleration.max()<=value.limits['max_support_shift_accel_mps2']+1e-8, \
        f'combined body acceleration {acceleration.max()} near {phases[index-1:index+2]}'
    yaw_acceleration=np.abs(np.diff(np.unwrap(yaws),n=2)/.02**2)
    assert yaw_acceleration.max()<=value.limits['max_accel_wz']+1e-8
