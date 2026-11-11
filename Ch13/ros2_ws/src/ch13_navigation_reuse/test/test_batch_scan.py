"""Official scalar-ray reference protects bounded batch optimization semantics."""
import math
from unittest.mock import patch
import mujoco,numpy as np,pytest
from ch13_navigation_reuse.scene import ray_scan,SCAN_POS
pytestmark=pytest.mark.skipif(mujoco.__version__!='3.13.0',reason='pinned batch API with normal argument')


def model_at(obstacle_x=1.5,offset=False):
    inertial='<inertial pos="0 0 0" quat="0.5 0.5 0.5 0.5" mass="1" diaginertia="1 1 1"/>' if offset else ''
    center='.3 .2 0' if offset else '0 0 0'
    model=mujoco.MjModel.from_xml_string(f'''<mujoco><worldbody>
      <geom type="box" pos="{obstacle_x} 0 .5" size=".1 .3 .3" group="5"/>
      <geom type="box" pos=".8 0 .5" size=".05 .3 .3" group="0"/>
      <body name="base" pos="0 0 .25"><freejoint/><geom type="sphere" size=".08" group="3" mass="1"/></body>
      <body name="target" pos="2 .6 .5"><freejoint/>{inertial}
       <geom type="cylinder" pos="{center}" size=".02 .04" group="5" mass=".02"/>
      </body></worldbody></mujoco>''')
    data=mujoco.MjData(model);mujoco.mj_forward(model,data);return model,data


def scalar_reference(model,data,count=181):
    mujoco.mj_kinematics(model,data)
    body=model.body('base').id;rotation=data.xmat[body].reshape(3,3)
    origin=data.xpos[body]+rotation@SCAN_POS;groups=np.zeros(6,dtype=np.uint8);groups[5]=1
    result=[]
    for angle in np.linspace(-math.pi,math.pi,count):
        direction=rotation@np.array([math.cos(angle),math.sin(angle),0.])
        distance=mujoco.mj_ray(model,data,origin,direction,groups,True,-1,np.zeros(1,dtype=np.int32))
        result.append(distance if .05<=distance<=4. else np.inf)
    return result


@pytest.mark.parametrize('angle',[0.,.7,1.1])
def test_level2_batches_native_calls_without_changing_rotated_centred_body_hits(monkeypatch,angle):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1');monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level2_obstacles')
    model,data=model_at();data.qpos[0]=.2
    data.qpos[10:14]=[math.cos(angle/2),math.sin(angle/2),0.,0.]
    expected=scalar_reference(model,data);q=data.qpos.copy()
    with patch.object(mujoco,'mj_multiRay',wraps=mujoco.mj_multiRay) as batch:
        actual=ray_scan(model,data)
    batch.assert_called_once()
    np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-10)
    np.testing.assert_array_equal(data.qpos,q)
    assert actual[90]==pytest.approx(.8)  # group0/self cannot replace the real wall hit


def test_offset_inertial_body_keeps_scalar_reference_for_known_upstream_culling_issue(monkeypatch):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1');monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level2_obstacles')
    model,data=model_at(offset=True);expected=scalar_reference(model,data)
    with patch.object(mujoco,'mj_multiRay',wraps=mujoco.mj_multiRay) as batch:
        actual=ray_scan(model,data)
    batch.assert_not_called();np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-10)


@pytest.mark.parametrize('profile,scenario',[('', ''),('carry_v1','level1_floor'),('carry_v1','level3_house')])
def test_other_profiles_keep_original_scalar_backend(monkeypatch,profile,scenario):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE',profile);monkeypatch.setenv('CH13_VALIDATION_SCENARIO',scenario)
    model,data=model_at();expected=scalar_reference(model,data)
    with patch.object(mujoco,'mj_multiRay',wraps=mujoco.mj_multiRay) as batch:actual=ray_scan(model,data)
    batch.assert_not_called();np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-10)


@pytest.mark.parametrize('position,finite',[(.54,False),(4.5,True),(4.6,False)])
def test_batch_keeps_original_near_and_four_metre_range_filter(monkeypatch,position,finite):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1');monkeypatch.setenv('CH13_VALIDATION_SCENARIO','level2_obstacles')
    model,data=model_at(obstacle_x=position);expected=scalar_reference(model,data)
    actual=ray_scan(model,data)
    np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-10)
    assert bool(np.isfinite(actual[90])) is finite
