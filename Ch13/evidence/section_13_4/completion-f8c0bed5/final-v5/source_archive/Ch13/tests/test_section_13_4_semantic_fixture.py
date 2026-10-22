"""Semantic fixture must be actual engine geometry, not injected RGB/detections."""
import importlib
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import mujoco

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))


def test_cup_fixture_compiles_in_mujoco_and_matches_gazebo_geometry(tmp_path):
    fixture = importlib.import_module('semantic_fixture_13_4')
    share = Path(__file__).resolve().parents[1]/'ros2_ws/src/integrated_robot_description'
    mj = fixture.make_cup_fixture('mujoco', share, tmp_path)
    model = mujoco.MjModel.from_xml_path(str(mj))
    assert model.ncam == 2
    assert mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, 'cup_bottom') >= 0
    assert mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, 'vision_fixture') == -1
    gz = fixture.make_cup_fixture('gazebo', share, tmp_path)
    world = ET.parse(gz)
    cup = world.find('.//model[@name="semantic_cup"]')
    assert cup.find('static').text == 'true'
    assert len(cup.findall('.//collision')) == len(ET.parse(mj).findall('./worldbody/geom'))
    assert cup.find('.//visual[@name="cup_bottom"]/geometry/cylinder/radius').text == '0.11'
    assert not world.findall('.//model[@name="vision_fixture"]')
    assert not world.findall('.//texture')  # all geometry authored here, no photo billboard
