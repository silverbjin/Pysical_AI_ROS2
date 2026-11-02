"""One native contact/QP/28-sample-geometry kernel; unchanged independent proof."""
import ctypes,importlib,importlib.util,json
from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_xyz import NativeXYZTransition
from test_native_xyz import assert_independent_primal

def api():
    name='integrated_robot_navigation.native_complete_xyz'
    assert importlib.util.find_spec(name),'kernel still crosses Python for contacts/QP/geometry separately'
    return importlib.import_module(name).CompleteXYZTransition

def case(name):return json.loads((Path(__file__).parent/'fixtures'/name).read_text())


def test_actual_job121_keeps_exact_nonlinear_servo_under_original_effort_limits():
    c=case('native_1a62_nonlinear_servo.json');assert c['provenance']['failed_job_id']==121
    model=compile_model(c['urdf'])
    with NativeMassEvaluator(model) as core:
        value=api()(model,c['limits'],native_mass=core)
        try:
            value.prepare();actual=value.step(**c['args'])
            assert_independent_primal(model,c['limits'],c['args'],actual,value.last_response)
            assert all(abs(torque)<=model.limits[n][3]+1e-6
                for n,torque in value.last_model['predicted_servo_command_efforts'].items())
            assert value.last_model['optimization_iterations']<=32
            assert value.last_model['compute_wall_ns']<=10_000_000
            assert value.last_model['future_geometry_validated'] is True
        finally:value.close()


def test_actual_parent_requires_exact_nonnegative_selected_z_after_numeric_reconstruction():
    c=case('native_5987_parent_bounds.json');assert c['provenance']['job_id']==57
    model=compile_model(c['urdf'])
    with NativeMassEvaluator(model) as core:
        value=api()(model,c['limits'],native_mass=core)
        try:
            value.prepare();actual=value.step(**c['args'])
            # Preserve the parent's existing HARD direction condition, even
            # for negative floating-point roundoff. Do not loosen its bound.
            assert actual[c['args']['foot']][2]>=0.
            assert_independent_primal(model,c['limits'],c['args'],actual,value.last_response)
            assert value.last_model['optimization_iterations']<=32
            assert value.last_model['compute_wall_ns']<=10_000_000
            assert value.last_model['future_geometry_validated'] is True
        finally:value.close()


def test_previous_success_input_does_not_reproduce_later_iteration_failure():
    c=case('native_ac904_xyz_iterations.json');model=compile_model(c['urdf'])
    with NativeMassEvaluator(model) as core:
        value=api()(model,c['limits'],native_mass=core)
        try:
            value.prepare();actual=value.step(**c['args'])
            assert_independent_primal(model,c['limits'],c['args'],actual,value.last_response)
            assert value.last_model['optimization_iterations']<=32
            assert value.last_model['compute_wall_ns']<=10_000_000
            assert value.last_model['inequality_residual']<=1e-7
            assert value.last_model['future_geometry_validated'] is True
        finally:value.close()


@pytest.mark.parametrize('fixture,job_id,expected_objective',[
    ('native_4d26_xyz_iterations.json',72,-4.89980590868478),
    ('native_48d0_xyz_iterations.json',130,22.6844709071878),
])
def test_bound_failed_jobs_converge_with_original_32_iterations_and_all_constraints(fixture,job_id,expected_objective):
    c=case(fixture);assert c['provenance']['failed_job_id']==job_id
    model=compile_model(c['urdf'])
    with NativeMassEvaluator(model) as core:
        value=api()(model,c['limits'],native_mass=core)
        try:
            value.prepare();actual=value.step(**c['args'])
            assert_independent_primal(model,c['limits'],c['args'],actual,value.last_response)
            assert value.last_model['optimization_iterations']<=32
            assert value.last_model['compute_wall_ns']<=10_000_000
            assert value.last_model['inequality_residual']<=1e-7
            assert value.last_model['future_geometry_validated'] is True
            # Independent full12 objective, anchored to separately recorded
            # offline original132+box oracle, not to the reduced solver output.
            a=c['args'];unit=a['speed']*a['dt'];response=np.asarray(value.last_response)*unit
            scale=max(np.linalg.svd(response,compute_uv=False)[0]**2,1e-12)
            desired=np.array([np.array(a['target_forces'].get(f,[0.,0.,0.]))-
                              a['forces_world'][f] for f in model.feet]).ravel()
            x=np.array([actual[f] for f in model.feet]).ravel()/unit
            h=response.T@response/scale+.001*np.eye(12);g=-response.T@desired/scale
            assert abs(.5*x@h@x+g@x-expected_objective)<1e-7
        finally:value.close()

@pytest.mark.parametrize('name',['native_141b_xyz_budget.json','native_76b_xyz_unload.json',
    'native_7e64_xyz_budget.json','native_9c62_xyz_budget.json'])
def test_same_real_problems_keep_full_forces_geometry_and_original_bounds(name):
    c=case(name);model=compile_model(c['urdf']);a=c['args']
    with NativeMassEvaluator(model) as core:
        old=NativeXYZTransition(model,c['limits'],terms_evaluator=core.contact_terms,force_objective='bounded_terminal_force')
        value=api()(model,c['limits'],native_mass=core)
        try:
            old.prepare();value.prepare();expected=old.step(**a);actual=value.step(**a)
            assert max(np.max(np.abs(np.array(actual[f])-expected[f])) for f in model.feet)<1e-10
            assert np.allclose(value.last_response,old.last_response,atol=1e-8,rtol=1e-10)
            assert_independent_primal(model,c['limits'],a,actual,value.last_response)
            for key in ('predicted_forces_world','predicted_servo_command_efforts'):
                for n,v in old.last_model[key].items():assert np.allclose(value.last_model[key][n],v,atol=1e-7,rtol=1e-9)
            assert value.last_model['kernel_backend']=='native_complete_1'
            assert value.last_model['optimization_iterations']<=32
            assert value.last_model['compute_wall_ns']<=10_000_000
        finally:value.close();old.close()

def test_kernel_does_not_reenter_fragmented_python_calculators(monkeypatch):
    c=case('native_9c62_xyz_budget.json');model=compile_model(c['urdf'])
    with NativeMassEvaluator(model) as core:
        value=api()(model,c['limits'],native_mass=core)
        try:
            value.prepare()
            def forbidden(*a,**kw):raise AssertionError('fragmented Python/native boundary called')
            monkeypatch.setattr(core,'contact_terms',forbidden)
            monkeypatch.setattr(value._optimizer,'solve',forbidden)
            monkeypatch.setattr(value.geometry,'evaluate',forbidden)
            assert value.step(**c['args'])
        finally:value.close()

@pytest.mark.parametrize('mutation',['nonfinite','bad_names','physical','singular_reference','future_geometry'])
def test_invalid_current_input_never_commits_a_candidate(mutation):
    c=case('native_9c62_xyz_budget.json');model=compile_model(c['urdf']);args=deepcopy(c['args'])
    if mutation=='nonfinite':args['body_pose'][0][0]=float('nan')
    elif mutation=='bad_names':args['points'].pop(model.feet[0])
    elif mutation=='physical':args['joints'][model.joint_names[0]]=100.
    elif mutation=='singular_reference':args['reference_pose'][0]=[0.,0.,0.,0.]
    elif mutation=='future_geometry':args['future_targets'][args['foot']]=[9.,9.,9.]
    with NativeMassEvaluator(model) as core:
        value=api()(model,c['limits'],native_mass=core)
        try:
            value.prepare()
            with pytest.raises(ValueError):value.step(**args)
            assert value.last_model is None
        finally:value.close()

def test_closing_a_borrowed_plan_blocks_further_numeric_calls():
    c=case('native_9c62_xyz_budget.json');model=compile_model(c['urdf']);core=NativeMassEvaluator(model)
    value=api()(model,c['limits'],native_mass=core)
    try:
        value.prepare();core.close()
        with pytest.raises(RuntimeError):value.step(**c['args'])
    finally:value.close();core.close()


@pytest.mark.parametrize('fault',['count','output_size','index','zero_budget','future_geometry'])
def test_native_abi_rejects_without_committing_output(fault):
    c=case('native_9c62_xyz_budget.json');model=compile_model(c['urdf'])
    with NativeMassEvaluator(model) as core:
        value=api()(model,c['limits'],native_mass=core)
        try:
            value.prepare();value.step(**c['args'])
            value._output.fill(123456.)
            count=len(value._input);size=len(value._output);budget=10_000_000
            indices=(ctypes.c_size_t*12)(*core._contact_indices)
            if fault=='count':count-=1
            elif fault=='output_size':size-=1
            elif fault=='index':indices[0]=0
            elif fault=='zero_budget':budget=0
            else:value._input[len(core.names)+112:len(core.names)+124]=9.
            code=value._call(value._optimizer._handle,core._handle,value.geometry._handle,
                value._input_ptr,count,len(core.names),indices,12,model.feet.index(c['args']['foot']),
                budget,value._output_ptr,size,value._timing_ptr,len(value._timings),value._error,len(value._error))
            assert code!=0
            assert np.all(value._output==123456.)
        finally:value.close()


def test_original_wall_cap_includes_python_validation_and_packing(monkeypatch):
    c=case('native_9c62_xyz_budget.json');model=compile_model(c['urdf'])
    with NativeMassEvaluator(model) as core:
        value=api()(model,c['limits'],native_mass=core)
        try:
            value.prepare();clock=iter((0,10_000_001))
            with monkeypatch.context() as patch:
                patch.setattr('integrated_robot_navigation.native_complete_xyz.time.perf_counter_ns',lambda:next(clock))
                with pytest.raises(ValueError,match='time budget'):value.step(**c['args'])
            assert value.last_model is None
            assert value.last_attempt['rejected_at']=='input_bounds'
        finally:value.close()
