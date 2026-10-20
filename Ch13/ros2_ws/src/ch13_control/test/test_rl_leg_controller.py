from ch13_control.rl_leg_controller import policy_command
from ch13_sim_core.locomotion_contract import create_policy_core
import numpy as np

def test_disabled_never_returns_motion_and_enabled_is_legs_only():
    core=create_policy_core()
    assert policy_command(core,np.zeros(12),False) is None
    names,values=policy_command(core,np.zeros(12),True)
    assert len(names)==len(values)==12
    assert all(not n.startswith(('arm','gripper')) for n in names)
