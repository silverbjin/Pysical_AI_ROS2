"""Reference geometry during a full turn; not physical engine acceptance.

982b8ca2 actually contacted rr_thigh_link/base_link during left SHIFT.
The original native contact fault remains mandatory and is not filtered.
"""
import math
import mujoco
import numpy as np
import pytest
from integrated_robot_navigation.geometry import navigation_mjcf
from gait_fixture import IdealFeedback
from test_gait import machine


@pytest.mark.parametrize('wz',[.03,-.03])
def test_full_turn_keeps_nonadjacent_thighs_clear_of_trunk(nav_robot_model,wz):
    plant=IdealFeedback(nav_robot_model);value=machine(nav_robot_model,plant)
    initial_xy=plant.pose[:2,3].copy()
    native=mujoco.MjModel.from_xml_string(navigation_mjcf(nav_robot_model));data=mujoco.MjData(native)
    trunk=native.geom('base_collision').id
    thighs=[next(g for g in range(native.ngeom) if native.geom_bodyid[g]==native.body(p+'_thigh_link').id)
        for p in ('fr','fl','rr','rl')]
    for tick in range(15000):
        result=value.advance(plant.state,(0.,0.,wz),plant.ros,plant.wall)
        assert result.state!='FAULT',dict(reason=result.reason,tick=tick,index=value._index,
            reference=value.reference_body.tolist(),targets={n:p.tolist() for n,p in value._targets.items()})
        plant.tick(value,result)
        if tick%10==0:
            for name,q in plant.state.joints.data['position'].items():
                data.qpos[native.jnt_qposadr[native.joint(name).id]]=q
            mujoco.mj_forward(native,data)
            for geom in thighs:
                distance=mujoco.mj_geomDistance(native,data,trunk,geom,.01,None)
                assert distance>=.0001,dict(tick=tick,phase=result.phase,
                    body=native.body(int(native.geom_bodyid[geom])).name,distance=distance,
                    yaw=math.atan2(value.travel[1,0],value.travel[0,0]))
        yaw=math.atan2(value.travel[1,0],value.travel[0,0])
        if abs(yaw)>=.3:
            for _ in range(150):
                result=value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
                assert result.state!='FAULT',result.reason
                plant.tick(value,result)
                if result.state=='STOPPED':
                    assert np.linalg.norm(plant.pose[:2,3]-initial_xy)<=.05, \
                        'ideal yaw/stop reference already exceeds the existing 5cm drift gate'
                    return
            pytest.fail('held yaw reference did not reach measured ideal STOPPED')
    pytest.fail('full turn did not complete within bounded ideal replay')
