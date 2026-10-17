from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from quadruped_rl import QuadrupedLocomotionEnv
from quadruped_rl_ros.gazebo_description import prepare_description


@pytest.mark.skipif(shutil.which('xacro') is None,reason='Source ROS Jazzy')
def test_real_urdf_joint_axes_origins_limits_and_bounded_position_plugins():
    repo=Path(__file__).resolve().parents[5]
    source=repo/'Ch11/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro'
    before=source.read_bytes()
    description=ET.fromstring(prepare_description(source))
    assert source.read_bytes()==before
    plugins=[p for p in description.findall('.//plugin') if
             p.get('name')=='gz::sim::systems::JointPositionController']
    assert len(plugins)==12
    with QuadrupedLocomotionEnv() as env:
        for index,name in enumerate(env.joint_names):
            joint=description.find(f"joint[@name='{name}']")
            assert joint is not None
            axis=np.fromstring(joint.find('axis').get('xyz'),sep=' ')
            assert np.allclose(axis,env.model.joint(name).axis)
            limit=joint.find('limit')
            assert np.allclose([float(limit.get('lower')),float(limit.get('upper'))],env._joint_limits[index])
            rpy=np.fromstring(joint.find('origin').get('rpy'),sep=' ')
            angle=0 if index%3==0 else 1.2 if index%3==1 else -2.4
            assert np.allclose(rpy,[0,angle,0])
            plugin=next(p for p in plugins if p.findtext('joint_name')==name)
            cap=20 if index%3==0 else 30
            assert float(plugin.findtext('cmd_max'))==cap
            assert float(plugin.findtext('cmd_min'))==-cap
            assert float(plugin.findtext('i_gain'))==0

            assert float(plugin.findtext('initial_position'))==[0.,-.5,1.][index%3]
