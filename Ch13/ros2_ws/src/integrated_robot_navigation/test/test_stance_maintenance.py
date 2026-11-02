"""Unsettled is a motion gate, not an instruction to stop torque feedback."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from test_async_xyz_owner import ready_xyz


def test_recorded_unsettled_window_has_safe_maintenance_candidates_without_relaxation():
    import json
    from pathlib import Path
    from integrated_robot_navigation.model import compile_model
    from integrated_robot_navigation.native_mass import NativeMassEvaluator
    from integrated_robot_navigation.native_complete_xyz import CompleteXYZTransition
    folder=Path(__file__).parent/'fixtures'
    c=json.loads((folder/'native_ab85_maintenance_window.json').read_text(encoding='utf-8-sig'))
    failed=json.loads((folder/'native_ab85_infeasible.json').read_text())
    model=compile_model(c['urdf'])
    with NativeMassEvaluator(model) as mass:
        k=CompleteXYZTransition(model,c['limits'],native_mass=mass)
        try:
            k.prepare()
            with pytest.raises(ValueError,match='Infeasible'):k.step(**failed['args'])
            for row in c['snapshots']:
                a=row['args'];delta=k.step(**a)
                assert max(np.linalg.norm(d) for d in delta.values())<=a['speed']*a['dt']+1e-12
                assert all(abs(t)<=model.limits[n][3]+1e-6 for n,t in k.last_model['predicted_servo_command_efforts'].items())
                assert k.last_model['optimization_iterations']<=32
                assert k.last_model['compute_wall_ns']<=10_000_000
                assert k.last_model['future_geometry_validated'] is True
                if row['maintenance']:
                    assert delta[a['foot']]==[0.,0.,0.]
                    assert a['target_forces']==a['forces_world']
        finally:k.close()


@pytest.mark.parametrize('timing',['strict','mature_horizon','same_cycle'])
def test_body_motion_stops_unload_but_same_cycle_still_maintains_stance(nav_robot_model,monkeypatch,timing):
    m,b,q,p,points,f=ready_xyz(nav_robot_model);m.load_result_timing=timing
    m._shift_plan=None;m._phase_start=m._last_ros-1_000_000_000;m._shift_duration=.7
    m._shift_settled_start=None;m._unload_start=m._last_ros-500_000_000
    m._offset_start=m.offset.copy();m._offset_goal=m.offset.copy()
    m._index=m.ORDER.index(f);m.swing_foot=f
    original=deepcopy(m._targets);requests=[]
    b=replace(b,body=replace(b.body,data={**b.body.data,'linear_velocity':(.0031,0.,0.),'angular_velocity':(0.,0.,0.)}))
    monkeypatch.setattr(m,'_margin',lambda *args,**kwargs:.04)
    monkeypatch.setattr(m,'_measure',lambda *args:(q,p,deepcopy(m.anchors),dict.fromkeys(m.model.feet,True),points,np.zeros(3)))
    monkeypatch.setattr(m,'_crawl_reference_time',lambda *args:(1.,.02))
    monkeypatch.setattr(m,'_solve',lambda *args,**kwargs:q)
    def transfer(*args,**kwargs):requests.append((args[-1],kwargs));return True
    monkeypatch.setattr(m,'_transfer_stance_load',transfer)
    result=m.advance(b,(.0001,0.,0.),m._last_ros+20_000_000,m._last_wall+20_000_000)
    assert result.state=='CRAWL' and result.phase=='SHIFT',result.reason
    assert m._unloaded_since is None,'unsettled body advanced the100ms release dwell'
    assert np.array_equal(m._targets[f],original[f]),'unsettled body moved the selected foot'
    if timing=='same_cycle':assert requests==[(.02,{'maintenance':True})]
    else:assert requests==[],'new feedback scope leaked into a legacy path'


def test_maintenance_requests_hold_selected_and_measured_force_not_unload_goal(nav_robot_model):
    m,b,q,p,points,f=ready_xyz(nav_robot_model);m.load_result_timing='same_cycle'
    args=m._spatial_arguments(q,p,points,f,.02,np.array(b.contacts.data['forces_world']),maintenance=True)
    assert args['allowed_z'][f]==(m._targets[f][2],m._targets[f][2])
    assert np.array_equal(args['future_targets'][f],m._targets[f])
    assert set(args['target_forces'])==set(m.model.feet)
    assert all(np.array_equal(args['target_forces'][foot],force) for foot,force in zip(m.model.feet,b.contacts.data['forces_world']))
    assert m.planning_reference_envelope[f]!=args['allowed_z'][f],'maintenance mutated full future envelope'


def test_same_cycle_parent_rejects_a_selected_foot_move_in_maintenance(nav_robot_model,monkeypatch):
    m,b,q,p,points,f=ready_xyz(nav_robot_model);m.load_result_timing='same_cycle'
    peer=m._load_transfer;before=deepcopy(m._targets)
    monkeypatch.setattr('integrated_robot_navigation.gait.time.monotonic_ns',lambda:m._last_wall)
    def transact(args,context):
        return {'delta':{n:[0.,0.,1e-5] if n==f else [0.,0.,0.] for n in m.model.feet},
            'context':context,'received_wall_ns':m._last_wall,'numeric_input':args,'job_id':1}
    peer.transact=transact
    with pytest.raises(ValueError,match='maintenance.*selected'):
        m._transfer_stance_load(b,q,p,points,f,.02,maintenance=True)
    assert all(np.array_equal(m._targets[n],before[n]) for n in m.model.feet)


def test_settled_release_cannot_reuse_a_maintenance_only_geometry_proof(nav_robot_model,monkeypatch):
    m,b,q,p,points,f=ready_xyz(nav_robot_model);m.load_result_timing='same_cycle'
    m._shift_plan=None;m._phase_start=m._last_ros-1_000_000_000;m._shift_duration=.7
    m._shift_settled_start=m._last_ros-200_000_000;m._unload_start=m._last_ros-500_000_000
    m._offset_start=m.offset.copy();m._offset_goal=m.offset.copy();m._index=m.ORDER.index(f)
    m.swing_foot=f;m._unloaded_since=m._last_ros-150_000_000
    m.load_transfer_observation={'outcome':'validated_numeric_result','maintenance':True}
    b=replace(b,body=replace(b.body,data={**b.body.data,'linear_velocity':(0.,0.,0.),'angular_velocity':(0.,0.,0.)}))
    loads={n:n!=f for n in m.model.feet}
    monkeypatch.setattr(m,'_margin',lambda *args,**kwargs:.04)
    monkeypatch.setattr(m,'_measure',lambda *args:(q,p,deepcopy(m.anchors),loads,points,np.zeros(3)))
    monkeypatch.setattr(m,'_crawl_reference_time',lambda *args:(1.,.02))
    monkeypatch.setattr(m,'_solve',lambda *args,**kwargs:q)
    monkeypatch.setattr(m,'_transfer_stance_load',lambda *args,**kwargs:True)
    result=m.advance(b,(.0001,0.,0.),m._last_ros+20_000_000,m._last_wall+20_000_000)
    assert result.state=='CRAWL' and result.phase=='SHIFT',result.reason
    assert m._unloaded_since is None,'a hold-only geometry proof authorized SWING'
