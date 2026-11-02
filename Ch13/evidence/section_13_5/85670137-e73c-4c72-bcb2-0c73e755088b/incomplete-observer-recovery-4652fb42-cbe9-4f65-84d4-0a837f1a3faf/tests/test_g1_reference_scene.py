"""The native reference experiment cannot leak into normal CRAWL or MuJoCo."""
import xml.etree.ElementTree as ET
import pytest
from integrated_robot_navigation.scene import materialize_scene


def test_g1_opt_in_changes_only_leg_reference_parameters_and_records_its_mode(tmp_path):
    original=materialize_scene('gazebo','g1',tmp_path/'original')
    changed=materialize_scene('gazebo','g1',tmp_path/'ramped',g1_reference_ramp=True)
    old=ET.parse(original['robot']['path'])
    new=ET.parse(changed['robot']['path'])
    assert changed['position_reference_mode']=='g1_ramp20ms'
    hardware=new.find('ros2_control/hardware')
    assert hardware.find("param[@name='ch13_g1_reference_experiment']").text=='true'
    enabled=[]
    for joint in new.findall('ros2_control/joint'):
        name=joint.get('name')
        ramp=joint.find("param[@name='ch13_reference_ramp_s']")
        previous=old.find(f"ros2_control/joint[@name='{name}']")
        if ramp is not None:
            assert ramp.text=='0.02'
            assert name.startswith(('fr_','fl_','rr_','rl_'))
            enabled.append(name)
        for key in ('ch13_kp','ch13_kd','ch13_native_damping','ch13_base_damping'):
            assert joint.find(f"param[@name='{key}']").text==previous.find(f"param[@name='{key}']").text
    assert len(enabled)==12
    for tag in ('link','joint'):
        assert [ET.tostring(e) for e in old.findall(tag)]==[ET.tostring(e) for e in new.findall(tag)]
    assert old.find("ros2_control/hardware/param[@name='ch13_g1_reference_experiment']") is None
    assert not old.findall("ros2_control/joint/param[@name='ch13_reference_ramp_s']")


@pytest.mark.parametrize('engine,scenario,enabled',[
    ('mujoco','g1',True),('gazebo','g2',True),('gazebo','front',True),('gazebo','g1','true')])
def test_invalid_reference_experiment_is_rejected_before_creating_a_scene(tmp_path,engine,scenario,enabled):
    output=tmp_path/'invalid'
    with pytest.raises(ValueError,match='G1|reference'):
        materialize_scene(engine,scenario,output,g1_reference_ramp=enabled)
    assert not output.exists()


def test_scene_metadata_cannot_hide_a_ramped_native_model(tmp_path):
    import json
    from integrated_robot_navigation.scene import load_scene
    record=materialize_scene('gazebo','g1',tmp_path/'ramped',g1_reference_ramp=True)
    record['position_reference_mode']='native'
    (tmp_path/'ramped/scene.json').write_text(json.dumps(record))
    with pytest.raises(ValueError,match='reference'):
        load_scene('gazebo',tmp_path/'ramped')


def test_ramped_scene_cannot_launch_as_normal_crawl(tmp_path):
    import importlib.util
    from pathlib import Path
    from launch import LaunchContext
    record=materialize_scene('gazebo','g1',tmp_path/'ramped',g1_reference_ramp=True)
    file=Path(__file__).resolve().parents[1]/'launch/crawl_system.launch.py'
    spec=importlib.util.spec_from_file_location('g1_reference_launch',file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    context=LaunchContext()
    context.launch_configurations.update(engine='gazebo',navigation_scene=str(tmp_path/'ramped'),
        carry_profile=str(tmp_path/'not-yet-read.json'),validation_mode='false')
    with pytest.raises(ValueError,match='reference.*validation'):
        module.launch_nodes(context)
