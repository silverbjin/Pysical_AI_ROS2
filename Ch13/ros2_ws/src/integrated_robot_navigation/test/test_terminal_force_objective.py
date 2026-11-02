"""Finite contact transition must use the existing feasible rate, not relax it."""
import inspect,json
from pathlib import Path
import numpy as np
import pytest
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_xyz import NativeXYZTransition
from integrated_robot_navigation.load_process import SpatialLoadProcess
from test_native_xyz import assert_independent_primal
from test_load_process import take


def case():
    data=json.loads((Path(__file__).parent/'fixtures/native_76b_xyz_unload.json').read_text())
    return compile_model(data['urdf']),data


def test_measured_timeout_input_uses_terminal_error_inside_identical_feasible_set():
    assert 'force_objective' in inspect.signature(NativeXYZTransition).parameters, 'six-second transition still uses an implicit one-per-second error decay'
    model,data=case();args=data['args'];feet=model.feet
    with NativeMassEvaluator(model) as core:
        old=NativeXYZTransition(model,data['limits'],terms_evaluator=core.contact_terms)
        new=NativeXYZTransition(model,data['limits'],terms_evaluator=core.contact_terms,force_objective='bounded_terminal_force')
        try:
            old.prepare();new.prepare();before=old.step(**args);after=new.step(**args)
            assert new.last_model['force_objective']=='bounded_terminal_force'
            assert_independent_primal(model,data['limits'],args,after,new.last_response)
            error=np.array([np.array(args['target_forces'].get(f,[0.,0.,0.]))-args['forces_world'][f] for f in feet]).ravel()
            old_force=new.last_response@np.array([before[f] for f in feet]).ravel()
            new_force=new.last_response@np.array([after[f] for f in feet]).ravel()
            assert np.linalg.norm(error-new_force)<np.linalg.norm(error-old_force)
            # This exact failure left both displacement and rate headroom.
            # Require a directional improvement, never a new safety threshold.
            assert after[args['foot']][2]>before[args['foot']][2]
        finally:old.close();new.close()


def test_actual_child_selects_and_pins_terminal_force_objective():
    model,data=case();worker=SpatialLoadProcess(model,command_space='stance_xyz',limits=data['limits'])
    try:
        assert worker.prepare().get('force_objective')=='bounded_terminal_force'
        worker.submit(data['args'],dict(foot=data['args']['foot']));take(worker)
        assert worker.last_model['force_objective']=='bounded_terminal_force'
        assert worker.snapshot()['force_objective']=='bounded_terminal_force'
    finally:worker.close()


def test_unknown_force_objective_cannot_prepare_a_reference():
    model,data=case()
    with pytest.raises(ValueError,match='force objective'):
        NativeXYZTransition(model,data['limits'],force_objective='unbounded')
