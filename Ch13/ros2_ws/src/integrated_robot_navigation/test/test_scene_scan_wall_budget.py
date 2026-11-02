"""Real converted sensor schedule, not a fabricated fresh scan/header."""
import xml.etree.ElementTree as ET
import pytest
import xacro
from integrated_robot_navigation.scene import materialize_scene,load_scene
from integrated_robot_navigation.geometry import description_dir


def test_gazebo_navigation_capture_rate_leaves_wall_age_budget_at_observed_slowdown(tmp_path):
    record=materialize_scene('gazebo','g1',tmp_path/'scene')
    robot=ET.parse(record['robot']['path']);converted=ET.parse(record['robot_sdf']['path'])
    sensor=robot.find('.//sensor[@name="navigation_lidar"]')
    rate=float(sensor.findtext('update_rate'))
    assert rate==20., '100ms simulation scan period exceeded300ms wall age at measured0.279RTF'
    assert int(sensor.findtext('lidar/scan/horizontal/samples'))==360
    assert sensor.findtext('lidar/visibility_mask')=='1'
    native=converted.find('.//sensor[@type="gpu_lidar"]')
    assert float(native.findtext('update_rate'))==rate
    # A budget calculation, not a guarantee of future wall scheduling.
    assert 1/rate/.279<.300
    camera=robot.find('.//sensor[@name="eye_in_hand"]')
    assert float(camera.findtext('update_rate'))==15.
    assert [int(camera.findtext('camera/image/'+k)) for k in ('width','height')]==[320,240]
    assert load_scene('gazebo',tmp_path/'scene')['robot']['sha256']==record['robot']['sha256']


def test_raw_xacro_keeps_existing_navigation_ten_hz_and_legacy_opt_out():
    path=description_dir()/'urdf/robot_system.urdf.xacro'
    legacy=ET.fromstring(xacro.process_file(str(path),mappings={'control_backend':'gazebo'}).toxml())
    old=ET.fromstring(xacro.process_file(str(path),mappings={'control_backend':'gazebo','navigation_enabled':'true'}).toxml())
    assert legacy.find('.//sensor[@name="navigation_lidar"]') is None
    assert float(old.findtext('.//sensor[@name="navigation_lidar"]/update_rate'))==10.
