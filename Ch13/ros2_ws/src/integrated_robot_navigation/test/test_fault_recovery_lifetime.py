"""Recovery ownership persists; final measured STOPPED remains strict."""
from dataclasses import replace
from test_fault_landing import unload_fault


def moving(bundle,v):
    return replace(bundle,body=replace(bundle.body,data={**bundle.body.data,'linear_velocity':(v,0.,0.)}))


def test_secondary_settle_error_keeps_known_landing_target_and_primary_reason(nav_robot_model):
    value,plant,foot=unload_fault(nav_robot_model)
    value._fail('fault landing measured support/settle lost')
    assert value._fault_landing_foot==foot, 'transient second fault destroyed the landing owner'
    assert value.reason=='measured unload timeout'
    assert [event['reason'] for event in value.fault_events]==[
        'measured unload timeout','fault landing measured support/settle lost']


def test_safe_landing_can_precede_final_velocity_settle_but_not_stop_confirmation(nav_robot_model):
    value,plant,foot=unload_fault(nav_robot_model);value.request_stop(urgent=True)
    v=(value.limits['stopped_v_mps']+value.limits['max_vx'])/2.
    result=value.advance(moving(plant.state,v),(0.,0.,0.),plant.ros,plant.wall)
    assert result.state=='STOPPING' and result.joint_targets is not None
    assert result.state!='STOPPED' and not value.fault_stop_confirmed
    assert value.reason=='measured unload timeout'


def test_wait_for_bounded_safe_entry_retains_target_until_fresh_data_allows_landing(nav_robot_model):
    value,plant,foot=unload_fault(nav_robot_model);value.request_stop(urgent=True)
    result=value.advance(moving(plant.state,1.1*value.limits['max_vx']),
        (0.,0.,0.),plant.ros,plant.wall)
    assert result.state=='FAULT' and result.joint_targets is None
    assert value._fault_landing_foot==foot
    plant.tick()
    result=value.advance(moving(plant.state,0.),(0.,0.,0.),plant.ros,plant.wall)
    assert result.state=='STOPPING' and result.joint_targets is not None
    assert value.reason=='measured unload timeout'


def test_fatal_owner_error_blocks_known_target_even_after_healthy_feedback(nav_robot_model):
    value,plant,foot=unload_fault(nav_robot_model);value._fail('owner:legs')
    value.request_stop(urgent=True)
    assert value._fault_landing_foot is None
    result=value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
    assert result.state=='FAULT' and result.joint_targets is None
    assert value.reason=='measured unload timeout'
    assert value.fault_events[-1]['reason']=='owner:legs'


def test_contact_already_present_does_not_end_fault_return_before_its_reference(nav_robot_model):
    value,plant,foot=unload_fault(nav_robot_model);value.request_stop(urgent=True)
    contact=plant.state.contacts
    forces=list(contact.data['forces']);touching=list(contact.data['touching'])
    i=value.model.feet.index(foot);forces[i]=2.2;touching[i]=True
    # Logic fixture for the native case: contact is present despite a raised
    # servo reference. This is not an ideal plant's physical force simulation.
    bundle=replace(plant.state,contacts=replace(contact,data={**contact.data,
        'forces':tuple(forces),'touching':tuple(touching)}))
    result=value.advance(bundle,(0.,0.,0.),plant.ros,plant.wall)
    assert result.state=='STOPPING' and value.swing_foot==foot
    assert value._land_goal[2]<=value._unload_origin_z
