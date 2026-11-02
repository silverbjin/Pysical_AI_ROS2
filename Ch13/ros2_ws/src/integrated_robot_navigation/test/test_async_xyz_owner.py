"""Parent owns bounded XYZ commits and full restoration, not the math child."""
from copy import deepcopy
import numpy as np
import pytest
from test_async_load_owner import ready,next_capture


def ready_xyz(model):
    m,b,q,p,points,f=ready(model);peer=m._load_transfer
    peer.command_space='stance_xyz'
    peer.last_model.update(command_space='stance_xyz',future_geometry_validated=True)
    from integrated_robot_navigation.compiled_reference import CompiledReferenceEnvelope
    m._reference_geometry=CompiledReferenceEnvelope(m.model,m.limits)
    peer.last_model['predicted_forces_world']={name:list(v) for name,v in zip(m.model.feet,b.contacts.data['forces_world'])}
    m._load_transfer_origin_xyz=deepcopy(m._targets)
    m.planning_future_targets=deepcopy(m._targets)
    return m,b,q,p,points,f


def complete_xyz(m,f,delta=None):
    peer=m._load_transfer
    if delta is None:
        delta={name:([0.,0.,1e-5] if name==f else [1e-5,-1e-5,0.]) for name in m.model.feet}
    peer.reply=dict(delta=delta,context=deepcopy(peer.pending),
        received_wall_ns=m._last_wall+20_000_000,submitted_wall_ns=m._last_wall,
        computed_wall_ns=m._last_wall+2_000_000)


def test_xyz_submission_uses_owned_transition_origins_and_future_geometry(nav_robot_model):
    m,b,q,p,points,f=ready_xyz(nav_robot_model)
    m._transfer_stance_load(b,q,p,points,f,.02)
    args=m._load_transfer.requests[0]
    assert 'reference_xyz' in args and 'reference_z' not in args
    assert all(np.array_equal(args['origins'][n],m._targets[n]) for n in m.model.feet)
    assert set(args['future_targets'])==set(m.model.feet)


def test_xyz_result_commits_once_and_restores_the_full_stance_vector(nav_robot_model):
    m,b,q,p,points,f=ready_xyz(nav_robot_model);before=deepcopy(m._targets)
    m._transfer_stance_load(b,q,p,points,f,.02);complete_xyz(m,f);b=next_capture(m,b)
    m._transfer_stance_load(b,q,p,points,f,.02)
    stance=next(n for n in m.model.feet if n!=f)
    assert np.allclose(m._targets[stance]-before[stance],[1e-5,-1e-5,0.],atol=1e-12)
    assert m.load_transfer_observation['applied_delta_xyz'][stance]==[1e-5,-1e-5,0.]
    m._discard_load_transfer();m.phase='SETTLE'
    assert m._restore_stance_load(.02)
    assert all(np.array_equal(m._targets[n],before[n]) for n in m.model.feet if n!=f)
    assert m._load_transfer_rest_xyz=={}


@pytest.mark.parametrize('bad',['vector_rate','selected_xy','selected_negative','total_vector','geometry_proof'])
def test_xyz_parent_rejects_unowned_or_over_limit_numeric_result(nav_robot_model,bad):
    m,b,q,p,points,f=ready_xyz(nav_robot_model)
    if bad=='total_vector':
        stance=next(n for n in m.model.feet if n!=f)
        m._load_transfer_origin_xyz[stance]=m._targets[stance]-np.array([.01,0.,0.])
    m._transfer_stance_load(b,q,p,points,f,.02);complete_xyz(m,f)
    if bad=='vector_rate':m._load_transfer.reply['delta'][f]=[0.,0.,.000041]
    elif bad=='selected_xy':m._load_transfer.reply['delta'][f]=[1e-5,0.,0.]
    elif bad=='selected_negative':m._load_transfer.reply['delta'][f]=[0.,0.,-5e-22]
    elif bad=='geometry_proof':m._load_transfer.last_model['future_geometry_validated']=False
    b=next_capture(m,b);before=deepcopy(m._targets)
    with pytest.raises(ValueError,match='transition optimization'):
        m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


def test_xyz_restore_speed_is_one_vector_cap_not_one_cap_per_axis(nav_robot_model):
    m,b,q,p,points,f=ready_xyz(nav_robot_model);m.phase='SETTLE'
    stance=next(n for n in m.model.feet if n!=f)
    original=m._targets[stance].copy();m._load_transfer_rest_xyz={stance:original+np.array([.003,.003,.003])}
    assert not m._restore_stance_load(.02)
    assert np.linalg.norm(m._targets[stance]-original)==pytest.approx(.002*.02,abs=1e-12)


def test_shorter_application_interval_scales_one_certified_segment_without_changing_rate(nav_robot_model):
    m,b,q,p,points,f=ready_xyz(nav_robot_model);m._load_transfer.last_model['linear_origin_feasible']=True
    before=deepcopy(m._targets);m._transfer_stance_load(b,q,p,points,f,.02)
    complete_xyz(m,f);b=next_capture(m,b,2_500_000)
    m._transfer_stance_load(b,q,p,points,f,.02)
    report=m.load_transfer_observation
    assert report['application_scaling']['fraction']==pytest.approx(.002*.0025/np.sqrt(2e-10))
    assert all(np.linalg.norm(m._targets[n]-before[n])<=.002*.0025+1e-12 for n in m.model.feet)
    fraction=report['application_scaling']['fraction']
    assert m._targets[f][2]-before[f][2]==pytest.approx(1e-5*fraction)
    assert len(m._load_transfer.requests)==2


def test_short_interval_without_convex_origin_proof_is_rejected(nav_robot_model):
    m,b,q,p,points,f=ready_xyz(nav_robot_model);before=deepcopy(m._targets)
    m._load_transfer.last_model['linear_origin_feasible']=False
    m._transfer_stance_load(b,q,p,points,f,.02);complete_xyz(m,f);b=next_capture(m,b,2_500_000)
    with pytest.raises(ValueError,match='elapsed reference rate'):m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


def test_scaled_segment_requires_current_exact_future_geometry(nav_robot_model):
    m,b,q,p,points,f=ready_xyz(nav_robot_model);before=deepcopy(m._targets)
    m.planning_future_targets[f][0]+=1.
    m._load_transfer.last_model['linear_origin_feasible']=True
    m._transfer_stance_load(b,q,p,points,f,.02);complete_xyz(m,f);b=next_capture(m,b,2_500_000)
    with pytest.raises(ValueError,match='geometry'):m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


def test_exact_recorded_job_is_safe_at_the_recorded_shorter_parent_interval():
    import json
    from pathlib import Path
    from integrated_robot_navigation.model import compile_model
    from integrated_robot_navigation.native_mass import NativeMassEvaluator
    from integrated_robot_navigation.load_xyz import SpatialXYZTransition
    from integrated_robot_navigation.compiled_reference import CompiledReferenceEnvelope
    from integrated_robot_navigation.gait import CrawlMachine
    from integrated_robot_navigation.samples import Sample,SensorBundle
    from integrated_robot_navigation.projection import body_rotation
    from test_async_load_owner import NumericPeer
    folder=Path(__file__).parent/'fixtures'
    case=json.loads((folder/'native_c371_xyz_budget.json').read_text())
    parent=json.loads((folder/'native_c371_parent_reply.json').read_text());a=case['args']
    assert parent['report_sha256']==case['report_sha256']
    model=compile_model(case['urdf']);limits=case['limits']
    with NativeMassEvaluator(model) as core:
        kernel=SpatialXYZTransition(model,limits,terms_evaluator=core.contact_terms);kernel.prepare()
        delta=kernel.step(**a);prediction=deepcopy(kernel.last_model)
    m=CrawlMachine(model,limits,load_transfer_policy='coupled_contact')
    peer=NumericPeer(kernel);peer.command_space='stance_xyz';peer.last_model=prediction
    m._load_transfer=peer;m._reference_geometry=CompiledReferenceEnvelope(model,limits)
    m.state='CRAWL';m.phase='SHIFT';m.generation=case['original_snapshot']['generation']
    m._unload_start=case['original_snapshot']['requested_ros_ns'];m._unload_origin_z=a['origins'][a['foot']][2]
    m._targets={f:np.array(p) for f,p in a['reference_xyz'].items()};before=deepcopy(m._targets)
    m.reference_body=np.array(a['reference_pose']);m._load_transfer_origin_xyz=deepcopy(a['origins'])
    m._stance_origin_z={f:p[2] for f,p in a['origins'].items()};m.planning_reference_envelope=a['allowed_z']
    m.planning_future_targets=a['future_targets'];m.load_balance_plan={'equilibrium':dict(feasible=True,forces_world=a['target_forces'])}
    m._last_ros=parent['ros_ns'];m._last_wall=parent['wall_ns']
    def tuples(value):return tuple(tuples(v) for v in value) if isinstance(value,list) else value
    context=deepcopy(case['original_snapshot'])
    for key in ('reference','geometry','capture'):context[key]=tuples(context[key])
    peer.reply=dict(delta=delta,context=context,received_wall_ns=parent['wall_ns'],
        submitted_wall_ns=context['requested_wall_ns'],computed_wall_ns=parent['wall_ns'])
    bundle=SensorBundle(**{k:Sample(**v) if v else None for k,v in parent['samples'].items()})
    pose=np.eye(4);pose[:3,:3]=body_rotation(bundle.body.data)[0];pose[:3,3]=bundle.body.data['position']
    m._transfer_stance_load(bundle,bundle.joints.data['position'],pose,
        dict(zip(model.feet,bundle.contacts.data['points'])),a['foot'],.012)
    report=m.load_transfer_observation;fraction=report['application_scaling']['fraction']
    assert 0.<fraction<1., 'the 18ms numeric proposal ignored the measured 12ms interval'
    assert max(np.linalg.norm(m._targets[f]-before[f]) for f in model.feet)<=.002*.012+1e-12
    assert all(np.allclose(m._targets[f]-before[f],fraction*np.array(delta[f]),atol=1e-12) for f in model.feet)
    assert len(peer.requests)==1
    assert all(np.allclose(peer.requests[0]['reference_xyz'][f],m._targets[f]) for f in model.feet)
