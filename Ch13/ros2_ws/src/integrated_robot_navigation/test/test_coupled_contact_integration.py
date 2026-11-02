"""Kernel ownership boundaries for the spatial position transition."""
from dataclasses import replace
import numpy as np
import pytest
from test_contact_support_plan import ready
from integrated_robot_navigation.contact_equilibrium import static_support


def fixture(model):
    m,plant,q,pose,com,points,support=ready(model)
    foot='rr_foot';m._index=m.ORDER.index(foot);m.swing_foot=foot
    m.phase='SHIFT';m._unload_start=plant.ros
    m._unload_origin_z=float(m._targets[foot][2])
    m._stance_origin_z={f:float(m._targets[f][2]) for f in m.model.feet}
    m.planning_reference_envelope={f:(z-.01,z+.01) for f,z in m._stance_origin_z.items()}
    current=static_support(m.model,q,pose,points,m.model.feet)
    target=static_support(m.model,q,pose,points,tuple(f for f in m.model.feet if f!=foot),min_force=0.)
    m.load_balance_plan={'equilibrium':target}
    vectors=tuple(tuple(current['forces_world'][f]) for f in m.model.feet)
    data={**plant.state.contacts.data,'forces_world':vectors,'force_vectors_valid':True,
        'forces':tuple(v[2] for v in vectors),'touching':tuple(v[2]>=2. for v in vectors)}
    bundle=replace(plant.state,contacts=replace(plant.state.contacts,data=data))
    return m,bundle,q,pose,points,foot


def test_coupled_profile_uses_spatial_controller_and_one_height_owner(nav_robot_model):
    m,bundle,q,pose,points,foot=fixture(nav_robot_model)
    assert hasattr(m._load_transfer,'step'), 'coupled mode still bound to the old scalar correction'
    before={f:p.copy() for f,p in m._targets.items()}
    assert m._transfer_stance_load(bundle,q,pose,points,foot,.02) is True
    report=m.load_transfer_observation
    assert report['selected_height_owner']=='coupled_optimizer'
    assert set(report['applied_delta_z'])==set(m.model.feet)
    assert all(abs(m._targets[f][2]-before[f][2])<=.002*.02+1e-12 for f in m.model.feet)
    after={f:p.copy() for f,p in m._targets.items()}
    assert m._transfer_stance_load(bundle,q,pose,points,foot,.02) is True
    assert all(np.array_equal(m._targets[f],after[f]) for f in m.model.feet)


@pytest.mark.parametrize('case',['missing','invalid','normal_mismatch'])
def test_scalar_support_alone_cannot_authorize_spatial_load_control(nav_robot_model,case):
    m,bundle,q,pose,points,foot=fixture(nav_robot_model)
    data=dict(bundle.contacts.data)
    if case=='missing':data.pop('forces_world')
    elif case=='invalid':data['force_vectors_valid']=False
    else:data['forces']=(99.,99.,99.,99.)
    bundle=replace(bundle,contacts=replace(bundle.contacts,data=data))
    with pytest.raises(ValueError,match='spatial force'):
        m._transfer_stance_load(bundle,q,pose,points,foot,.02)
