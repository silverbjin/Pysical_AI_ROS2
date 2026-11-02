"""Integrated ideal-feedback sequencing only, never physical G1 acceptance."""
import numpy as np

from gait_fixture import IdealFeedback
from test_gait import machine


def test_g1_measures_small_inplace_lift_then_returns_without_full_walk_bump(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model,plant)
    origin = value.floor['fl_foot']
    value.request_contact_calibration()
    previous, held = None,None
    maximum, saw_return, done = 0.,False,False
    for _ in range(400):
        result = value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        if result.phase=='SWING' and held is None:
            held = {name:point.copy() for name,point in value._targets.items()}
        if held is not None:
            for name in nav_robot_model.feet:
                if name!='fl_foot': assert np.allclose(value._targets[name],held[name],atol=1e-12)
            point = value._targets['fl_foot']
            assert np.allclose(point[:2],held['fl_foot'][:2],atol=1e-12)
            if previous is not None: assert np.linalg.norm(point-previous)/.02<=.020000001
            previous = point.copy()
            maximum = max(maximum,float(point[2]-origin))
        saw_return |= result.phase=='TOUCHDOWN'
        plant.tick(value,result)
        if held is not None and result.state=='STAND':
            done = True
            break
    assert done and saw_return
    assert .006<=maximum<=.010, 'G1 must not execute the unrelated full20mm walking bump'
    snapshot = value.calibration_snapshot()
    assert len(snapshot['vertical']['lift_captures'])==3
    assert value._phase_start==snapshot['stages'][-1]['ros_ns'], 'reported phase origin must follow real transition'
    assert snapshot['vertical']['scope']=='candidate_requires_owner_measured_stand_settle'
    assert snapshot['request']['deadline_wall_ns']==snapshot['request']['wall_ns']+20_000_000_000


def test_g1_unload_keeps_bounded_progress_during_low_force_confirmation(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model,plant)
    value.request_contact_calibration()
    for _ in range(400):
        result = value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        plant.tick(value,result)
        if result.phase=='SHIFT' and not plant.state.contacts.data['touching'][1]: break
    else: raise AssertionError('test fixture never unloaded selected foot')
    before = value._targets['fl_foot'][2]
    result = value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
    after = value._targets['fl_foot'][2]
    assert result.phase=='SHIFT', '100ms confirmation cannot be bypassed'
    assert 0<after-before<=.002*.02000001, 'do not stall on either side of the2N boundary'
