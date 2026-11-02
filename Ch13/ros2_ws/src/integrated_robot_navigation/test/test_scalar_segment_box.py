"""Same capsule geometry with fixed triples, including collision boundaries."""
import math
from dataclasses import replace
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from integrated_robot_navigation.leg_kinematics import _segment_box_distance
from integrated_robot_navigation import leg_kinematics as legs
from integrated_robot_vision.kinematics import origin_matrix
from segment_box_reference import numpy_segment_box_distance


@pytest.mark.parametrize('start,end,half,expected',[
    ((-2.,0.,0.),(2.,0.,0.),(1.,1.,1.),0.),
    ((2.,0.,0.),(2.,1.,0.),(1.,1.,1.),1.),
    ((2.,2.,2.),(2.,2.,2.),(1.,1.,1.),math.sqrt(3.)),
    ((-2.,2.,2.),(2.,2.,2.),(1.,1.,1.),math.sqrt(2.)),
    ((1.+1e-12,0.,0.),(1.+1e-12,1.,0.),(1.,1.,1.),1e-12),
    ((-1.,0.,0.),(1.,0.,0.),(0.,0.,0.),0.),
])
def test_segment_distance_accepts_fixed_vec3_without_array_construction(start,end,half,expected):
    assert _segment_box_distance(start,end,half)==pytest.approx(expected,abs=1e-14)


def test_scalar_distance_matches_frozen_numpy_geometry_and_reversal():
    rng=np.random.default_rng(20261028)
    for _ in range(1500):
        start,end=rng.uniform(-.6,.6,size=(2,3));half=rng.uniform(.005,.3,size=3)
        expected=numpy_segment_box_distance(start,end,half)
        actual=_segment_box_distance(tuple(start),tuple(end),tuple(half))
        assert actual==pytest.approx(expected,abs=1e-13)
        assert _segment_box_distance(tuple(end),tuple(start),tuple(half))==pytest.approx(actual,abs=1e-13)


@pytest.mark.parametrize('start,end,half',[
    ((math.nan,0.,0.),(0.,0.,0.),(1.,1.,1.)),
    ((0.,0.,0.),(math.inf,0.,0.),(1.,1.,1.)),
    ((0.,0.),(0.,0.,0.),(1.,1.,1.)),
    ((0.,0.,0.),(0.,0.,0.),(-1.,1.,1.)),
])
def test_invalid_distance_geometry_is_rejected(start,end,half):
    with pytest.raises(ValueError):_segment_box_distance(start,end,half)


@pytest.mark.parametrize('xyz,rpy',[
    ('0 0 0','0 0 0'),('0.02 -0.01 0.03','0 0 0'),
    ('0.02 -0.01 0.03','0.15 -0.1 0.3'),
])
def test_transformed_capsule_keeps_original_urdf_geometry(nav_robot_model,xyz,rpy):
    tree=ET.fromstring(nav_robot_model.urdf)
    base=tree.find("link[@name='base_link']/collision")
    origin=base.find('origin')
    if origin is None:origin=ET.SubElement(base,'origin')
    origin.set('xyz',xyz);origin.set('rpy',rpy)
    # Synthetic collision-origin variation only; never an engine/model change.
    model=replace(nav_robot_model,urdf=ET.tostring(tree,encoding='unicode'))
    inverse=np.linalg.inv(origin_matrix(origin))
    half=np.asarray([float(v)/2 for v in base.find('geometry/box').get('size').split()])
    rng=np.random.default_rng(20261028)
    for foot in model.feet:
        hip,offset,upper,_,_=legs._leg_spec(model.urdf,foot)
        radius=float(tree.find(f"link[@name='{foot[:2]}_thigh_link']/collision/geometry/cylinder").get('radius'))
        for _ in range(30):
            q=tuple(rng.uniform((-.2,-.6,.7),(.2,-.3,1.3)))
            roll,thigh,_=q;c,s=math.cos(roll),math.sin(roll)
            start=hip+np.array([0.,offset*c,offset*s])
            end=start+np.array([-upper*math.sin(thigh),upper*math.cos(thigh)*s,-upper*math.cos(thigh)*c])
            a=(inverse@np.r_[start,1.])[:3];b=(inverse@np.r_[end,1.])[:3]
            expected=numpy_segment_box_distance(a,b,half)-radius
            assert legs.thigh_trunk_clearance(model,foot,q)==pytest.approx(expected,abs=1e-13)
