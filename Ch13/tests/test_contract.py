from pathlib import Path
import numpy as np
import pytest
import yaml
from ch13_sim_core.contract import load_contract, ordered_values

CONFIG = Path(__file__).parents[1] / 'config/joint_contract.yaml'
NAMES = [f'{leg}_{joint}_joint' for leg in ('fr', 'fl', 'rr', 'rl')
         for joint in ('hip', 'thigh', 'calf')] + [f'arm_joint_{i}' for i in range(1, 7)] + ['gripper_left_joint', 'gripper_right_joint']

def test_contract_has_12_leg_6_arm_2_gripper_joints():
    c = load_contract(CONFIG)
    assert list(c.names) == NAMES
    assert [len(g.names) for g in c.groups.values()] == [12, 6, 2]
    np.testing.assert_allclose(c.nominal[:3], [0, -.5, 1])

def test_contract_rejects_duplicate_joint_names(tmp_path):
    raw = yaml.safe_load(CONFIG.read_text())
    raw['groups']['arm']['names'][0] = 'fr_hip_joint'
    file = tmp_path / 'bad.yaml'
    file.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError): load_contract(file)

def test_ordered_values_is_name_based():
    np.testing.assert_array_equal(ordered_values(['b', 'extra', 'a'], [2, 99, 1], ['a', 'b']), [1, 2])

@pytest.mark.parametrize('names,values', [(['b'], [1]), (['a','a'],[1,2]), (['a','b'],[1,float('nan')]), (['a','b'],[1]), (['a','b'],[1,float('inf')])])
def test_ordered_values_rejects_missing_duplicate_and_nonfinite_values(names, values):
    with pytest.raises(ValueError): ordered_values(names, values, ['a','b'])

@pytest.mark.parametrize('field,value', [('lower',[4]*6), ('nominal',[0]*5), ('upper',[float('nan')]*6)])
def test_rejects_invalid_dimensions_or_limits(tmp_path, field, value):
    raw = yaml.safe_load(CONFIG.read_text())
    raw['groups']['arm'][field] = value
    file = tmp_path/'invalid.yaml'
    file.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError): load_contract(file)
