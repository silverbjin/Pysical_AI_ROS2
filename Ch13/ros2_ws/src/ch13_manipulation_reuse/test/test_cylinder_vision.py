import numpy as np
import pytest
from ch13_manipulation_reuse.cylinder_vision import fit_cylinder


def image():
    v,u=np.mgrid[:240,:320];dy=-(u-159.5)/230.;dz=-(v-119.5)/230.
    center=np.array([.5,.01,.54]);radius=.02
    a=1+dy*dy;b=-2*(center[0]+dy*center[1]);c=center[0]**2+center[1]**2-radius**2
    determinant=b*b-4*a*c;t=(-b-np.sqrt(np.maximum(0.,determinant)))/(2*a)
    valid=(determinant>=0)&(t>0)&(abs(.54+dz*t-center[2])<=.04)
    rgb=np.zeros((240,320,3),dtype=np.uint8);rgb[valid]=[210,8,8]
    depth=np.full((240,320),np.inf,dtype=np.float32);depth[valid]=t[valid]
    transform=np.array([[0.,0.,1.,0.],[-1.,0.,0.,0.],[0.,-1.,0.,.54],[0.,0.,0.,1.]])
    return rgb,depth,[230.,230.,159.5,119.5],transform,center


def test_known_upright_cylinder_center_comes_from_actual_depth_surface():
    rgb,depth,k,transform,center=image()
    result=fit_cylinder(rgb,depth,k,transform,.02,.08)
    np.testing.assert_allclose(result['center'],center,atol=.002)
    assert result['residual_m']<.0001 and result['points']>20
    assert result['yaw_observed'] is False


def test_historical_camera_transform_is_used_without_oracle_center():
    rgb,depth,k,transform,center=image();transform[:3,3]+=[1.2,-.2,.3]
    result=fit_cylinder(rgb,depth,k,transform,.02,.08)
    np.testing.assert_allclose(result['center'],center+[1.2,-.2,.3],atol=.002)


def test_occluded_height_or_invalid_depth_is_not_a_center_observation():
    rgb,depth,k,transform,_=image();rgb[:120]=0
    with pytest.raises(ValueError):fit_cylinder(rgb,depth,k,transform,.02,.08)
    rgb,depth,k,transform,_=image();depth[:]=np.nan
    with pytest.raises(ValueError):fit_cylinder(rgb,depth,k,transform,.02,.08)


def test_invalid_calibration_rejected():
    rgb,depth,k,transform,_=image();k[0]=0.
    with pytest.raises(ValueError):fit_cylinder(rgb,depth,k,transform,.02,.08)


def test_disconnected_red_robot_fragment_does_not_expand_target_height():
    rgb,depth,k,transform,center=image()
    rgb[5:20,140:165]=[230,0,0];depth[5:20,140:165]=.25
    result=fit_cylinder(rgb,depth,k,transform,.02,.08)
    np.testing.assert_allclose(result['center'],center,atol=.002)
    assert result['box']['height']<100


def test_visible_top_and_bottom_can_share_one_geometric_cylinder():
    rgb,depth,k,transform,center=image()
    rgb[116:124]=0
    rgb[5:20,140:165]=[230,0,0];depth[5:20,140:165]=.25
    result=fit_cylinder(rgb,depth,k,transform,.02,.08)
    np.testing.assert_allclose(result['center'],center,atol=.002)
    assert result['components_used']==2
