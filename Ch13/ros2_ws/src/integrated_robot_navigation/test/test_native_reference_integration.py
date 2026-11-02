"""Native reference arithmetic is owned, pinned and explicitly released."""
import pytest
from test_spatial_xyz_transition import xyz_inputs
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.native_reference import NativeReferenceEnvelope
from integrated_robot_navigation.load_xyz import SpatialXYZTransition
from integrated_robot_navigation.load_process import SpatialLoadProcess


def test_xyz_kernel_uses_native_geometry_and_reports_its_exact_binary(nav_robot_model):
    model,a=xyz_inputs(nav_robot_model);kernel=SpatialXYZTransition(model,default_limits())
    try:
        assert isinstance(kernel.geometry,NativeReferenceEnvelope),'10ms worker still evaluates current geometry in Python'
        kernel.step(**a)
        assert kernel.last_model['geometry_backend']=='native_reference_28_current_samples'
        assert kernel.last_model['geometry_library_sha256']==kernel.geometry.provenance['library_sha256']
    finally:
        if hasattr(kernel.geometry,'close'):kernel.geometry.close()


def test_real_xyz_worker_pins_reference_binary_and_closes_it_before_ack(nav_robot_model):
    model,_=xyz_inputs(nav_robot_model)
    with NativeReferenceEnvelope(model,default_limits()) as geometry:
        expected=geometry.provenance['library_sha256']
    worker=SpatialLoadProcess(model,command_space='stance_xyz',limits=default_limits(),
        expected_reference_library_sha256=expected)
    try:assert worker.prepare()['reference_library_sha256']==expected
    finally:closed=worker.close()
    assert closed['reference_geometry_closed'] is True
    assert closed['acknowledged'] and closed['parent_reaped']


def test_wrong_reference_binary_cannot_prepare_or_retry(nav_robot_model):
    model,_=xyz_inputs(nav_robot_model)
    worker=SpatialLoadProcess(model,command_space='stance_xyz',limits=default_limits(),
        expected_reference_library_sha256='0'*64)
    try:
        with pytest.raises(ValueError,match='preparation'):worker.prepare()
        with pytest.raises(ValueError,match='latched'):worker.prepare()
    finally:worker.close()
