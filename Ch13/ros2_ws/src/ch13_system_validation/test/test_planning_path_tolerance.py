import importlib.util
from pathlib import Path
import pytest

@pytest.mark.parametrize('profile,scenario,expected', [('', 'level3_house', None),
    ('carry_v1','development',None),('carry_v1','level2_obstacles',None),
    ('carry_v1','level3_house',.001)])
def test_totg_margin_is_level3_only_and_keeps_final_validation(monkeypatch,profile,scenario,expected):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE',profile)
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO',scenario)
    source=Path(__file__).resolve().parents[2]/'ch13_navigation_reuse/launch/navigation.launch.py'
    spec=importlib.util.spec_from_file_location('totg_launch',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    config=module.planning_parameters()
    assert config['ompl'].get('path_tolerance')==expected
    assert config['ompl']['response_adapters']==[
        'default_planning_response_adapters/AddTimeOptimalParameterization',
        'default_planning_response_adapters/ValidateSolution']
    assert config['robot_description_planning']['joint_limits']['joint1']['max_velocity']==.5
