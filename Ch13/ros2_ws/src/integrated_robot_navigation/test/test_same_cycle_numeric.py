"""One current-snapshot transaction, not a retry of a stale optimized result."""
from copy import deepcopy
import json,time
from pathlib import Path
import numpy as np
import pytest
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_complete_xyz import CompleteXYZTransition
from integrated_robot_navigation.load_process import SpatialLoadProcess,assess_numeric_close
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.samples import Sample,SensorBundle
from integrated_robot_navigation.projection import body_rotation


def recorded():
    c=json.loads((Path(__file__).parent/'fixtures/native_dbdf_current_servo.json').read_bytes())
    assert c['provenance']['job_id']==325 and c['provenance']['last_reply']['ok'] is True
    return c,compile_model(c['urdf'])


def test_same_original_success_is_unsafe_at_the_recorded_newer_snapshot():
    c,model=recorded();a=c['args'];current=c['parent']['fault']['samples']['joints']['data']['position']
    with NativeMassEvaluator(model) as mass:
        k=CompleteXYZTransition(model,c['limits'],native_mass=mass)
        try:
            k.prepare();delta=k.step(**a)
            target={f:np.asarray(a['reference_xyz'][f])+delta[f] for f in model.feet}
            exact,_,_=k.geometry.evaluate(joints=current,body=np.array(a['reference_pose']),targets=target,
                envelope=a['allowed_z'],selected=a['foot'],future_targets=a['future_targets'])
            assert abs(k.gains['fl_calf_joint']*(exact['fl_calf_joint']-current['fl_calf_joint']))>30.+1e-6
        finally:k.close()


def test_same_cycle_uses_current_capture_once_and_keeps_exact_limits():
    c,model=recorded();a=c['args'];fault=c['parent']['fault'];m=None
    with NativeMassEvaluator(model) as mass:
        m=CrawlMachine(model,c['limits'],mass_evaluator=mass,load_transfer_policy='coupled_contact',
            async_load_transfer=True,load_result_timing='same_cycle',load_receipt_mode='event_receiver')
        try:
            m.prepare_load_transfer();m.state='CRAWL';m.phase='SHIFT';m.generation=0
            m._unload_start=fault['phase_context']['_unload_start'];m._unload_origin_z=a['origins'][a['foot']][2]
            m._targets={f:np.array(p) for f,p in a['reference_xyz'].items()};before=deepcopy(m._targets)
            m.reference_body=np.array(a['reference_pose']);m._load_transfer_origin_xyz=deepcopy(a['origins'])
            m._stance_origin_z={f:p[2] for f,p in a['origins'].items()};m.planning_reference_envelope=a['allowed_z']
            m.planning_future_targets=a['future_targets'];m.load_balance_plan={'equilibrium':dict(feasible=True,forces_world=a['target_forces'])}
            m._last_ros=fault['ros_ns'];m._last_wall=time.monotonic_ns()
            offset=m._last_wall-fault['wall_ns'];samples=deepcopy(fault['samples'])
            for value in samples.values():
                if value:value['received_ns']+=offset
            bundle=SensorBundle(**{key:Sample(**value) if value else None for key,value in samples.items()})
            pose=np.eye(4);pose[:3,:3]=body_rotation(bundle.body.data)[0];pose[:3,3]=bundle.body.data['position']
            q=bundle.joints.data['position'];points=dict(zip(model.feet,bundle.contacts.data['points']))
            assert m._transfer_stance_load(bundle,q,pose,points,a['foot'],a['dt']) is True
            assert m.load_transfer_observation['numeric_input']['joints']==q
            assert m.load_transfer_observation['application_scaling']['scope']=='same_cycle_elapsed_credit_not_future_horizon'
            assert m._load_transfer.snapshot()['submitted']==m._load_transfer.snapshot()['completed']==1
            assert not m._load_transfer.snapshot()['pending']
            assert m.load_transfer_observation['queued_next'] is False
            assert max(np.linalg.norm(m._targets[f]-before[f]) for f in model.feet)<=a['speed']*a['dt']+1e-12
            exact=m._solve(q,True)
            assert all(abs(m._load_transfer.gains[n]*(exact[n]-q[n]))<=model.limits[n][3]+1e-6 for n in model.joint_names)
            assert m._load_transfer.last_transaction['wall_ns']<=10_000_000
            assert m._transfer_stance_load(bundle,q,pose,points,a['foot'],a['dt']) is True
            assert m._load_transfer.snapshot()['submitted']==1,'same capture submitted twice'
        finally:closed=m.close_load_transfer()
    closed.update(model_sha256=model.model_sha256,owner_pid=closed['pid']+1)
    assert assess_numeric_close(closed,model.model_sha256)


def test_transaction_timeout_never_retries_or_exposes_a_late_result(monkeypatch):
    c,model=recorded();p=SpatialLoadProcess(model,command_space='stance_xyz',limits=c['limits'],receipt_mode='event_receiver')
    try:
        p.prepare()
        def late(_):time.sleep(.012);return True
        monkeypatch.setattr(p._receipts,'wait_message',late)
        with pytest.raises(ValueError,match='same-cycle.*deadline'):p.transact(c['args'],{'generation':0})
        assert p.snapshot()['last_transaction']['wall_ns']>10_000_000
        assert 'deadline' in p.snapshot()['last_transaction']['error']
        assert p.snapshot()['submitted']==1 and p.snapshot()['completed']==0
        assert p.snapshot()['pending']
        with pytest.raises(ValueError,match='latched'):p.transact(c['args'],{'generation':0})
        assert p.snapshot()['submitted']==1
    finally:closed=p.close()
    assert closed['acknowledged'] and closed['parent_reaped'] and closed['receiver_joined']


def test_same_cycle_rejects_non_event_or_non_async_configuration(nav_robot_model):
    from integrated_robot_navigation.carry_profile import default_limits
    for kwargs in ({},{'async_load_transfer':True}):
        with pytest.raises(ValueError,match='same.cycle|timing'):
            CrawlMachine(nav_robot_model,default_limits(),load_transfer_policy='coupled_contact',load_result_timing='same_cycle',**kwargs)
