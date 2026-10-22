"""Only the vision workflow opts into the separately named repaired controller."""
import importlib.util
from pathlib import Path

import pytest
import yaml

PKG=Path(__file__).resolve().parents[1]/'ros2_ws/src/integrated_robot_description'


@pytest.mark.parametrize('engine',['mujoco','gazebo'])
def test_vision_uses_isolated_controller_without_changing_legacy_configuration(engine):
    path=PKG/'launch'/f'{engine}.launch.py'
    spec=importlib.util.spec_from_file_location('ch13_controller_'+engine,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source=PKG/'config/controllers.yaml'
    original=source.read_bytes()
    legacy=yaml.safe_load(Path(module.materialize_controller_config(source)).read_text())
    vision=yaml.safe_load(Path(module.materialize_controller_config(source,vision=True)).read_text())
    arm=lambda data:data['controller_manager']['ros__parameters']['arm_trajectory_controller']
    assert arm(legacy)['type']=='joint_trajectory_controller/JointTrajectoryController'
    assert arm(vision)['type']=='integrated_robot_controller/JointTrajectoryController'
    arm(vision)['type']=arm(legacy)['type']
    assert vision==legacy and source.read_bytes()==original
