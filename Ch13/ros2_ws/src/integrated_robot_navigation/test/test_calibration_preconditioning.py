"""Loaded compression release is not an airborne swing or a physical G1 PASS."""
import pytest
import numpy as np
from integrated_robot_navigation import calibration
from integrated_robot_navigation.carry_profile import default_limits
from gait_fixture import IdealFeedback
from test_gait import machine


def step(z=.01675,rest=.01675,measured=.04,forces=(35.,35.,35.,35.),dt=.02):
    assert hasattr(calibration,'precondition_loaded_reference'), 'bounded loaded preconditioning missing'
    return calibration.precondition_loaded_reference(z=z,rest_z=rest,measured_reference_z=measured,
        forces=forces,dt=dt,limits=default_limits())


def test_loaded_reference_slew_and_original_unload_bound():
    assert step()==pytest.approx(.01679)
    z=.01675
    for _ in range(300): z=step(z=z)
    assert z==pytest.approx(.02675)  # immutable original rest+10mm; no renewed envelope


def test_loaded_virtual_reference_is_not_capped_by_physical_floor():
    # Actual Gazebo: target rest+3mm held1.08ROSsec while measured FL>=18.5N.
    # A virtual preload reference crossing floor does not mean actual lift.
    assert step(z=.01975)==pytest.approx(.01979)
    assert step(z=.0198)==pytest.approx(.01984)
    assert step(z=.0198,forces=(35.,9.,35.,35.))==.0198


def test_no_tracking_compression_means_no_early_unload_on_stiff_ground():
    assert step(z=.0198,measured=.0198)==.0198
    assert step(z=.0198,measured=.0197)==.0198
    assert step(z=.0198,measured=.01982)==pytest.approx(.01981)
    with pytest.raises(ValueError): step(measured=float('nan'))


def test_low_load_reserve_holds_without_synthesizing_a_new_contact():
    assert step(forces=(35.,9.,35.,35.))==.01675
    assert step(forces=(35.,10.,35.,35.))==pytest.approx(.01679)


@pytest.mark.parametrize('forces',[(35.,1.9,35.,35.),(1.9,35.,35.,35.),(35.,35.,0.,35.)])
def test_any_premature_contact_loss_is_failure_not_a_retry(forces):
    with pytest.raises(ValueError,match='preconditioning support'):
        step(forces=forces)


@pytest.mark.parametrize('dt',[-.01,float('nan'),.201])
def test_invalid_time_never_advances_preconditioning(dt):
    with pytest.raises(ValueError): step(dt=dt)


def test_explicit_calibration_selects_fl_even_after_a_previous_walk(nav_robot_model):
    plant=IdealFeedback(nav_robot_model)
    value=machine(nav_robot_model,plant)
    value._index=2
    value.request_contact_calibration()
    assert value.ORDER[value._index]=='fl_foot', 'G1 force index and selected foot must agree'


def test_stiff_follower_holds_before_settled_unload_preserving_rest_and_other_feet(nav_robot_model):
    plant=IdealFeedback(nav_robot_model)
    value=machine(nav_robot_model,plant)
    original=float(value._targets['fl_foot'][2])
    held={name:point.copy() for name,point in value._targets.items()}
    value.request_contact_calibration()
    saw_progress=saw_unload=False
    for _ in range(220):
        result=value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        if value._shift_plan is None and value.phase=='SHIFT' and value._unload_start is None:
            saw_progress |= value._targets['fl_foot'][2]>original+1e-6
            assert value._targets['fl_foot'][2]<=original+value.limits['max_unload_height_m']+1e-12
        for name in nav_robot_model.feet:
            if name!='fl_foot': assert np.allclose(value._targets[name],held[name],atol=1e-12)
        plant.tick(value,result)
        if value._unload_start is not None:
            saw_unload=True
            assert value._unload_origin_z==original, 'preconditioning must not renew the10mm unload allowance'
            assert value.calibration_snapshot()['preconditioning_rest_z']==original
            break
    assert not saw_progress, 'perfect joint tracking has no compression to release before settled unload'
    assert saw_unload, 'fixture must actually check the original-rest unload handoff'
