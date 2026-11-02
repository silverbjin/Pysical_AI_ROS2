"""One valid reply may mature; never scale an infeasible origin or bypass ages."""
from copy import deepcopy
import numpy as np
import pytest
from test_async_xyz_owner import ready_xyz,complete_xyz
from test_async_load_owner import next_capture


def waiting(model,monkeypatch):
    m,b,q,p,points,f=ready_xyz(model);m.load_result_timing='mature_horizon'
    m._load_transfer.last_model['linear_origin_feasible']=False
    before=deepcopy(m._targets)
    m._transfer_stance_load(b,q,p,points,f,.02);complete_xyz(m,f)
    monkeypatch.setattr('integrated_robot_navigation.gait.time.monotonic_ns',lambda:m._last_wall)
    b=next_capture(m,b,2_500_000)
    m._transfer_stance_load(b,q,p,points,f,.02)
    return m,b,q,p,points,f,before


def test_unscaled_reply_waits_for_both_original_clocks_then_commits_once(nav_robot_model,monkeypatch):
    m,b,q,p,points,f,before=waiting(nav_robot_model,monkeypatch);peer=m._load_transfer
    assert m.load_transfer_observation['outcome']=='waiting_for_reference_horizon'
    assert m._load_collected_reply is not None and len(peer.requests)==1
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)
    b=next_capture(m,b,20_000_000)
    m._transfer_stance_load(b,q,p,points,f,.02)
    assert m._load_collected_reply is None and len(peer.requests)==2
    assert m.load_transfer_observation['application_scaling']['fraction']==1.
    assert any(not np.array_equal(before[n],m._targets[n]) for n in m.model.feet)
    applied=deepcopy(m._targets)
    m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(applied[n],m._targets[n]) for n in m.model.feet)


@pytest.mark.parametrize('invalid',['age','generation','stop'])
def test_waiting_never_outlives_snapshot_ownership_or_stop(nav_robot_model,monkeypatch,invalid):
    m,b,q,p,points,f,before=waiting(nav_robot_model,monkeypatch)
    if invalid=='stop':m.request_stop(urgent=True)
    else:
        b=next_capture(m,b,201_000_000 if invalid=='age' else 20_000_000)
        if invalid=='generation':m.generation+=1
        with pytest.raises(ValueError,match='stale original|ownership'):
            m._transfer_stance_load(b,q,p,points,f,.02)
    assert m._load_collected_reply is None
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


def test_horizon_policy_requires_explicit_async_coupled_scope(nav_robot_model):
    from integrated_robot_navigation.gait import CrawlMachine
    from integrated_robot_navigation.carry_profile import default_limits
    with pytest.raises(ValueError,match='timing|horizon'):
        CrawlMachine(nav_robot_model,default_limits(),load_result_timing='mature_horizon')


def test_exact_successful_job64_needs_more_original_ros_time_and_cannot_be_scaled():
    import json
    from pathlib import Path
    from integrated_robot_navigation.model import compile_model
    from integrated_robot_navigation.native_mass import NativeMassEvaluator
    from integrated_robot_navigation.native_complete_xyz import CompleteXYZTransition
    case=json.loads((Path(__file__).parent/'fixtures/native_3357_parent_horizon.json').read_bytes())
    assert case['provenance']['job_id']==64
    model=compile_model(case['urdf'])
    with NativeMassEvaluator(model) as mass:
        kernel=CompleteXYZTransition(model,case['limits'],native_mass=mass)
        try:
            kernel.prepare();delta=kernel.step(**case['args'])
            assert kernel.last_model['linear_origin_feasible'] is False
            largest=max(np.linalg.norm(d) for d in delta.values())
            old=case['original_context'];cutoff=case['parent_cutoff'];speed=case['limits']['unload_speed_mps']
            elapsed=min(cutoff['ros_ns']-old['requested_ros_ns'],cutoff['wall_ns']-old['requested_wall_ns'])/1e9
            assert 0.<elapsed<largest/speed<=old['dt']+1e-12
        finally:kernel.close()
