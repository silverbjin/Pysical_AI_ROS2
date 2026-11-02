"""Reference ownership persists through 100ms release confirmation.

Synthetic force inputs isolate hybrid control; native stability remains required.
"""
from dataclasses import replace
import pytest
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.carry_profile import default_limits
from gait_fixture import IdealFeedback
from test_stance_load_transfer import helper


@pytest.mark.parametrize('policy',['geometric','stance_admittance'])
def test_unload_reference_scope_and_100ms_confirmation(nav_robot_model,policy):
    model=helper(nav_robot_model).model;plant=IdealFeedback(model)
    machine=CrawlMachine(model,default_limits(),load_transfer_policy=policy)
    machine.reset(plant.state,plant.ros,plant.wall)
    for _ in range(500):
        previous=machine.advance(plant.state,(.0001,0.,0.),plant.ros,plant.wall)
        assert previous.state!='FAULT',previous.reason
        if machine._unload_start is not None:break
        plant.tick(machine,previous)
    else:pytest.fail('fixture never reached a measured unload')
    foot=machine.ORDER[machine._index];index=model.feet.index(foot)
    plant.tick(machine,previous)
    forces=list(plant.state.contacts.data['forces']);touching=list(plant.state.contacts.data['touching'])
    forces[index]=1.9;touching[index]=False
    plant.state=replace(plant.state,
        contacts=replace(plant.state.contacts,data={**plant.state.contacts.data,'forces':forces,'touching':touching}),
        body=replace(plant.state.body,data={**plant.state.body.data,'linear_velocity':(0.,0.,0.),'angular_velocity':(0.,0.,0.)}))
    old=machine._targets[foot][2]
    result=machine.advance(plant.state,(.0001,0.,0.),plant.ros,plant.wall)
    assert result.state!='FAULT',result.reason
    assert result.phase=='SHIFT' and machine._unloaded_since==plant.ros
    delta=machine._targets[foot][2]-old
    if policy=='stance_admittance':
        assert 0<delta<=.002*.02+1e-12, 'first low sample ended regulation before confirmation'
    else:assert delta==0., 'the explicit G2 experiment leaked into the ordinary policy'
    first=plant.ros
    for step in range(1,6):
        plant.tick(machine,result)
        forces=list(plant.state.contacts.data['forces']);touching=list(plant.state.contacts.data['touching'])
        forces[index]=1.9;touching[index]=False
        plant.state=replace(plant.state,
            contacts=replace(plant.state.contacts,data={**plant.state.contacts.data,'forces':forces,'touching':touching}),
            body=replace(plant.state.body,data={**plant.state.body.data,'linear_velocity':(0.,0.,0.),'angular_velocity':(0.,0.,0.)}))
        result=machine.advance(plant.state,(.0001,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        assert plant.ros-first==step*20_000_000
        assert result.phase==('SHIFT' if step<5 else 'SWING'), '100ms physical release dwell changed'


@pytest.mark.parametrize('expired',[False,True])
def test_height_ceiling_holds_reference_only_until_original_unload_deadline(nav_robot_model,expired):
    model=helper(nav_robot_model).model;plant=IdealFeedback(model)
    plant.ros+=100_000_000_000;plant.wall+=100_000_000_000;plant.tick(follow=False)
    machine=CrawlMachine(model,default_limits(),load_transfer_policy='stance_admittance')
    machine.reset(plant.state,plant.ros,plant.wall)
    for _ in range(500):
        previous=machine.advance(plant.state,(.0001,0.,0.),plant.ros,plant.wall)
        assert previous.state!='FAULT',previous.reason
        if machine._unload_start is not None:break
        plant.tick(machine,previous)
    else:pytest.fail('fixture never reached unload')
    foot=machine.ORDER[machine._index]
    plant.tick(machine,previous)
    machine._unload_start=plant.ros-(6_010_000_000 if expired else 5_750_000_000)
    machine._targets[foot][2]=machine._unload_origin_z+.010
    plant.state=replace(plant.state,body=replace(plant.state.body,
        data={**plant.state.body.data,'linear_velocity':(0.,0.,0.),'angular_velocity':(0.,0.,0.)}))
    ceiling=machine._targets[foot][2]
    result=machine.advance(plant.state,(.0001,0.,0.),plant.ros,plant.wall)
    if expired:
        assert result.state=='FAULT' and result.joint_targets is None
    else:
        assert result.state=='CRAWL' and result.phase=='SHIFT', 'height cap prematurely ended the original6s budget'
        assert machine._targets[foot][2]==ceiling
