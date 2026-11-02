"""All candidate routes must apply the same actuator-aware support contract."""
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from gait_fixture import IdealFeedback
from test_stance_load_transfer import helper
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.support import center_of_mass


def ready(model,*,tiny=False):
    model=helper(model).model
    if tiny:
        tree=ET.fromstring(model.urdf)
        for n in model.joint_names:tree.find(f"joint[@name='{n}']/limit").set('effort','.001')
        model=compile_model(ET.tostring(tree,encoding='unicode'))
    m=CrawlMachine(model,default_limits(),load_transfer_policy='coupled_contact')
    plant=IdealFeedback(model);plant.tick();m.reset(plant.state,plant.ros,plant.wall)
    assert m.state!='FAULT',m.reason
    m.state='CRAWL';q=plant.state.joints.data['position'];pose=m.reference_body.copy()
    com=np.asarray(center_of_mass(model,q,pose))
    points=dict(zip(model.feet,plant.state.contacts.data['points']))
    support=[points[f] for f in model.feet if f!=m.ORDER[m._index]]
    return m,plant,q,pose,com,points,support


@pytest.mark.parametrize('route',['search','projection'])
def test_tiny_actuator_caps_are_rejected_by_both_search_routes(nav_robot_model,route):
    m,plant,q,pose,com,points,support=ready(nav_robot_model,tiny=True)
    if route=='search':
        m._begin_shift(com,{f:True for f in m.model.feet},points,plant.ros,q)
        generator=m._shift_plan
    else:
        generator=m._constrained_shift(support,.025,q,pose,com,com,0.,0.,dict(m._targets))
    with pytest.raises(ValueError):list(generator)
    assert m.support_feasibility_evaluations>0, 'candidate route skipped the common physical evaluator'


def test_accepted_search_reports_three_contact_effort_feasibility(nav_robot_model):
    m,plant,q,pose,com,points,support=ready(nav_robot_model)
    m._begin_shift(com,{f:True for f in m.model.feet},points,plant.ros,q)
    list(m._shift_plan)
    record=m.load_balance_plan
    assert record['scope']=='actuation_aware_common_support_plan'
    physical=record['equilibrium']
    assert physical['feasible'] and physical['torque_utilization']<=1.+1e-8
    assert set(physical['forces_world'])==set(m.model.feet)-{m.ORDER[m._index]}
    assert record['search_method'] in ('direction','projection')


def test_common_plan_contract_does_not_enable_it_in_default_or_calibration(nav_robot_model):
    m,plant,q,pose,com,points,support=ready(nav_robot_model)
    m.calibrating=True
    assert m._support_actuation(q,pose,com,points) is None
    original=CrawlMachine(m.model,m.limits)
    assert original._support_actuation(q,pose,com,points) is None
