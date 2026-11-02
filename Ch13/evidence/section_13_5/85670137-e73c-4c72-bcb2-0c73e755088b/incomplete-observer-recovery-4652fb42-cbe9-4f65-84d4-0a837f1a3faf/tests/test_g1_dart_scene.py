"""An explicit numerical-contact experiment needs a distinct physics binding."""
import json
import xml.etree.ElementTree as ET
import pytest
from integrated_robot_navigation.scene import materialize_scene,load_scene


def test_contact_allowance_binds_actual_plugin_and_native_physics_without_changing_robot(tmp_path):
    base=materialize_scene('gazebo','g1',tmp_path/'base',g1_reference_ramp=True)
    changed=materialize_scene('gazebo','g1',tmp_path/'contact',g1_reference_ramp=True,g1_contact_allowance=True)
    assert changed['dart_contact_mode']=='allowance50um'
    assert changed['native_physics_sha256']!=base['native_physics_sha256']
    old=ET.parse(base['robot']['path']);new=ET.parse(changed['robot']['path'])
    for tag in ('link','joint','ros2_control'):
        assert [ET.tostring(e) for e in old.findall(tag)]==[ET.tostring(e) for e in new.findall(tag)]
    for path in ('robot','robot_sdf'):
        tree=ET.parse(changed[path]['path'])
        plugin=tree.find(".//plugin[@filename='navigation_gazebo_observer']")
        assert plugin.findtext('g1_validation_contact_experiment')=='true'
        assert float(plugin.findtext('g1_contact_allowance_m'))==.00005
    assert load_scene('gazebo',tmp_path/'contact')['native_physics_sha256']==changed['native_physics_sha256']


@pytest.mark.parametrize('engine,scenario,ramp,enabled',[
    ('mujoco','g1',False,True),('gazebo','g2',False,True),('gazebo','g1',False,True),('gazebo','g1',True,'true')])
def test_contact_option_cannot_leave_the_approved_g1_comparison(tmp_path,engine,scenario,ramp,enabled):
    with pytest.raises(ValueError,match='contact|G1'):
        materialize_scene(engine,scenario,tmp_path/'invalid',g1_reference_ramp=ramp,g1_contact_allowance=enabled)
    assert not (tmp_path/'invalid').exists()


def test_contact_mode_cannot_be_hidden_in_metadata(tmp_path):
    record=materialize_scene('gazebo','g1',tmp_path/'scene',g1_reference_ramp=True,g1_contact_allowance=True)
    record['dart_contact_mode']='native'
    (tmp_path/'scene/scene.json').write_text(json.dumps(record))
    with pytest.raises(ValueError,match='contact|physics'):
        load_scene('gazebo',tmp_path/'scene')
