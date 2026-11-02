"""Compiled immutable geometry must match independent current-input checks."""
import importlib.util,json
from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.reference_envelope import reference_constraints
from integrated_robot_navigation.leg_kinematics import fk_leg


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.compiled_reference'), \
        'full IK/URDF validation is repeated for every future grid point'
    from integrated_robot_navigation.compiled_reference import CompiledReferenceEnvelope
    return CompiledReferenceEnvelope


def fixture():
    case=json.loads((Path(__file__).parent/'fixtures/native_c371_xyz_budget.json').read_text())
    model=compile_model(case['urdf']);a=case['args']
    return model,case['limits'],dict(joints=a['joints'],body=a['reference_pose'],
        targets=a['reference_xyz'],envelope=a['allowed_z'],selected=a['foot'],future_targets=a['future_targets'])


def assert_same(model,limits,evaluator,args):
    old=reference_constraints(model,limits,**args);new=evaluator.evaluate(**args)
    assert old[0].keys()==new[0].keys()
    assert max(abs(old[0][n]-new[0][n]) for n in old[0])<2e-12
    assert np.allclose(old[1],new[1],atol=2e-12,rtol=0.)
    assert np.allclose(old[2],new[2],atol=2e-12,rtol=0.)


def test_exact_actual_job_keeps_all_nominal_and_future_grid_residuals():
    model,limits,a=fixture();evaluator=api()(model,limits)
    assert_same(model,limits,evaluator,a)


def test_random_current_q_and_reference_pose_do_not_reuse_previous_results():
    model,limits,a=fixture();evaluator=api()(model,limits);rng=np.random.default_rng(123)
    for index in range(64):
        q=dict(a['joints']);body=np.eye(4);angle=rng.uniform(-.2,.2)
        body[:2,:2]=[[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]
        body[:3,3]=rng.uniform(-.2,.2,3);targets={}
        for f in model.feet:
            angles=[rng.uniform(-.15,.15),rng.uniform(-.8,-.4),rng.uniform(.9,1.5)]
            for part,value in zip(('hip','thigh','calf'),angles):q[f[:2]+'_'+part+'_joint']=value
            targets[f]=(body@np.r_[fk_leg(model,f,angles),1.])[:3]
        future=deepcopy(targets);selected=model.feet[index%4];future[selected][:2]+=[.001,-.001]
        args=dict(joints=q,body=body,targets=targets,
            envelope={f:(p[2]-.0005,p[2]+.0005) for f,p in targets.items()},selected=selected,future_targets=future)
        assert_same(model,limits,evaluator,args)


def test_current_evaluation_does_not_repeat_public_full_ik_or_fk_validation(monkeypatch):
    from integrated_robot_navigation import leg_kinematics as module
    model,limits,a=fixture();evaluator=api()(model,limits)
    def unexpected(*args,**kwargs):raise AssertionError('repeated full geometry validation')
    for name in ('ik_leg','fk_leg','thigh_trunk_clearance'):monkeypatch.setattr(module,name,unexpected)
    q,clear,bounds=evaluator.evaluate(**a)
    assert set(q)==set(a['joints']) and len(clear)==4 and len(bounds)==24


@pytest.mark.parametrize('bad',['target_nan','future_nan','envelope_nan','missing_foot','unreachable','bad_joint'])
def test_invalid_or_unreachable_current_input_cannot_obtain_geometry_proof(bad):
    model,limits,a=fixture();evaluator=api()(model,limits)
    f=a['selected']
    if bad=='target_nan':a['targets'][f][0]=float('nan')
    elif bad=='future_nan':a['future_targets'][f][0]=float('nan')
    elif bad=='envelope_nan':a['envelope'][f]=[0.,float('nan')]
    elif bad=='missing_foot':del a['targets'][f]
    elif bad=='unreachable':a['future_targets'][f][0]+=1.
    else:a['joints']['fr_hip_joint']=10.
    with pytest.raises(ValueError):evaluator.evaluate(**a)
