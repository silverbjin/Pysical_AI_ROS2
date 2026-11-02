"""Native current-q contact arithmetic equals independent Python statics."""
from dataclasses import replace
import numpy as np
import pytest
from test_contact_equilibrium import inputs
from integrated_robot_navigation.contact_equilibrium import leg_terms
from integrated_robot_navigation.native_mass import NativeMassEvaluator


def test_native_contact_terms_match_full_link_python_at_current_inputs(nav_robot_model):
    rng=np.random.default_rng(130530)
    with NativeMassEvaluator(nav_robot_model) as value:
        assert hasattr(value,'contact_terms'),'spatial load calculation bypasses compiled geometry'
        for _ in range(40):
            q={n:float(rng.uniform(bounds[0],bounds[1])) for n,bounds in nav_robot_model.limits.items()}
            axis=rng.normal(size=3);axis/=np.linalg.norm(axis);angle=rng.uniform(-.3,.3)
            from integrated_robot_navigation.contact_equilibrium import skew
            cross=skew(axis);pose=np.eye(4)
            pose[:3,:3]+=np.sin(angle)*cross+(1.-np.cos(angle))*(cross@cross)
            pose[:3,3]=rng.uniform(-1.,1.,3)
            points={f:rng.uniform(-.5,.5,3) for f in nav_robot_model.feet}
            expected=leg_terms(nav_robot_model,q,pose,points)
            actual=value.contact_terms(nav_robot_model,q,pose,points)
            for a,b in zip(actual,expected):
                assert set(a)==set(b)
                for f in nav_robot_model.feet:assert np.allclose(a[f],b[f],rtol=0.,atol=2e-12)


def test_native_contact_terms_revalidate_current_point_and_lifetime(nav_robot_model):
    args=inputs(nav_robot_model);value=NativeMassEvaluator(nav_robot_model)
    q,pose,points=(args[n] for n in ('joints','body_pose','points'))
    first=value.contact_terms(nav_robot_model,q,pose,points)
    points={f:np.asarray(p)+[.01,.02,-.01] for f,p in points.items()}
    second=value.contact_terms(nav_robot_model,q,pose,points)
    assert not np.allclose(first[0]['fr_foot'],second[0]['fr_foot'])
    q=dict(q);q['fr_hip_joint']=float('nan')
    with pytest.raises(ValueError):value.contact_terms(nav_robot_model,q,pose,points)
    value.close()
    with pytest.raises(RuntimeError,match='closed'):value.contact_terms(nav_robot_model,q,pose,points)


@pytest.mark.parametrize('kind',['missing_point','nonfinite_point','changed_mass'])
def test_native_contact_terms_reject_invalid_model_and_points(nav_robot_model,kind):
    args=inputs(nav_robot_model);q,pose,points=(args[n] for n in ('joints','body_pose','points'))
    model=nav_robot_model
    if kind=='missing_point':points.pop('fr_foot')
    elif kind=='nonfinite_point':points['fr_foot']=[float('inf'),0.,0.]
    else:
        masses=dict(model.masses);m,p=masses['fr_thigh_link'];masses['fr_thigh_link']=(2*m,p)
        model=replace(model,masses=masses)
    with NativeMassEvaluator(nav_robot_model) as value:
        with pytest.raises(ValueError):value.contact_terms(model,q,pose,points)


def test_actual_transition_matches_with_shared_compiled_kinematics():
    import json
    from pathlib import Path
    from integrated_robot_navigation.model import compile_model
    from integrated_robot_navigation.load_transition import SpatialLoadTransition
    data=json.loads((Path(__file__).parent/'fixtures/native_26a3_spatial_budget.json').read_text())
    model=compile_model(data['urdf'])
    with NativeMassEvaluator(model) as core:
        value=SpatialLoadTransition(model,terms_evaluator=core.contact_terms)
        value.prepare();result=value.step(**data['args'])
        assert result==pytest.approx(data['expected_delta'],abs=1e-9)
        assert value.last_model['scope']=='spatial_spring_prediction_not_measured_force_or_torque'
