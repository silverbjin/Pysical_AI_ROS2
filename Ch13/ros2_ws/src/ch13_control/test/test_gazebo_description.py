from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import math
from ch13_sim_core.contract import load_contract

def test_twenty_unique_position_controllers_with_safe_initial_targets():
    p=Path(__file__).parents[2]/'ch13_robot_description/urdf/integrated_robot.urdf.xacro'
    root=ET.fromstring(subprocess.check_output(['xacro',str(p)]))
    plugins=root.findall(".//plugin[@name='gz::sim::systems::JointPositionController']")
    c=load_contract()
    assert len(plugins)==20
    assert {p.findtext('joint_name') for p in plugins}==set(c.names)
    assert len({p.findtext('topic') for p in plugins})==20
    for p in plugins:
        assert all(math.isfinite(float(p.findtext(k))) for k in ('p_gain','d_gain','cmd_max','cmd_min','initial_position'))
        i=c.names.index(p.findtext('joint_name'))
        assert float(p.findtext('initial_position'))==c.nominal[i]
