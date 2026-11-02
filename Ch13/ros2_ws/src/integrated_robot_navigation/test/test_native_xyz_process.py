"""Actual child must identify/release the pinned optimizer, not just exit."""
import json,hashlib
from pathlib import Path
import pytest
from integrated_robot_navigation.load_process import SpatialLoadProcess,assess_numeric_close
from integrated_robot_navigation.native_xyz import optimizer_library_path
from integrated_robot_navigation.model import compile_model
from test_load_process import take


def fixture():
    case=json.loads((Path(__file__).parent/'fixtures/native_141b_xyz_budget.json').read_text())
    return compile_model(case['urdf']),case


def test_actual_child_uses_native_backend_and_closes_both_arithmetic_handles():
    model,case=fixture();worker=SpatialLoadProcess(model,command_space='stance_xyz',limits=case['limits'])
    try:
        ready=worker.prepare()
        assert ready.get('optimization_backend')=='qpmad_1_5_1_native','actual child still executes Python/SLSQP'
        assert ready.get('kernel_backend')=='native_complete_1','actual child still crosses Python for each arithmetic stage'
        assert ready.get('complete_kernel_abi')==1
        assert ready['optimization_library_sha256']==hashlib.sha256(optimizer_library_path().read_bytes()).hexdigest()
        worker.submit(case['args'],dict(generation=1));reply=take(worker)
        assert worker.last_model['optimization_backend']==ready['optimization_backend']
        assert worker.last_model['optimization_library_sha256']==ready['optimization_library_sha256']
        assert worker.last_model['kernel_backend']==ready['kernel_backend']
        assert reply['context']==dict(generation=1)
        assert worker.snapshot()['optimization_library_sha256']==ready['optimization_library_sha256']
    finally:closed=worker.close()
    assert closed['reference_geometry_closed'] and closed['optimizer_closed']
    assert closed['complete_kernel_closed'] is True
    closed.update(model_sha256=model.model_sha256,owner_pid=closed['pid']+1)
    assert assess_numeric_close(closed,model.model_sha256)
    broken={**closed,'optimizer_closed':False};assert not assess_numeric_close(broken,model.model_sha256)
    broken={**closed,'complete_kernel_closed':False};assert not assess_numeric_close(broken,model.model_sha256)


def test_mismatched_native_optimizer_cannot_prepare_or_retry():
    model,case=fixture();worker=SpatialLoadProcess(model,command_space='stance_xyz',limits=case['limits'],
        expected_optimizer_library_sha256='0'*64)
    try:
        with pytest.raises(ValueError,match='preparation'):worker.prepare()
        with pytest.raises(ValueError,match='latched'):worker.prepare()
    finally:worker.close()
