"""Solver initialization precedes activation; rejection keeps bounded timing."""
from types import SimpleNamespace
import pytest
from test_spatial_load_transition import api,inputs


def test_solver_preparation_is_idempotent_and_emits_no_motor_reference(nav_robot_model):
    model,_=inputs(nav_robot_model);value=api()(model)
    prepared=value.prepare()
    assert prepared['scope']=='numeric_solver_initialization_not_contact_admission'
    assert prepared['solver_verified'] is True and prepared['calls']==1
    assert value.prepare()==prepared
    assert value.last_model is None and value.last_attempt is None


def test_failed_preparation_cannot_allow_configure(nav_robot_model,monkeypatch):
    from integrated_robot_navigation import load_transition as module
    model,_=inputs(nav_robot_model);value=api()(model)
    monkeypatch.setattr(module,'minimize',lambda *a,**k:SimpleNamespace(
        status=9,success=False,message='forced setup failure'))
    with pytest.raises(ValueError,match='solver preparation'):value.prepare()
    assert value.preparation is None


def test_solver_rejection_keeps_stage_cpu_and_wall_observations(nav_robot_model,monkeypatch):
    from integrated_robot_navigation import load_transition as module
    model,args=inputs(nav_robot_model);value=api()(model)
    def reject(*a,**k):
        k['callback'](None)
        return SimpleNamespace(status=9,success=False,message='forced solve failure')
    monkeypatch.setattr(module,'minimize',reject)
    with pytest.raises(ValueError,match='transition optimization'):value.step(**args)
    trace=value.last_attempt
    assert trace['scope']=='current_attempt_timing_not_force_measurement'
    assert 'constraints_ready' in trace['stages'] and 'solver_iteration' in trace['stages']
    assert trace['stages']['constraints_ready']['wall_ns']>0
    assert trace['stages']['constraints_ready']['thread_cpu_ns']>0
    assert value.last_model is None
